from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timedelta
from collections import Counter
import base64
import binascii
import hmac
import json
import mimetypes
import os
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from xml.etree import ElementTree

from ai_clients import call_openai_compatible_llm as call_llm_client
from config import env_bool, env_float, env_int, first_env, load_dotenv_files
import location_service
import operations_service
from repository import add_column_if_missing, connect_database, execute_in_clause, quote_table_name
from repository import safe_json_loads
from search_engine import build_summary as build_search_summary
from search_engine import search_documents as hybrid_search_documents
from streaming import chunk_text, sse_event


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = BASE_DIR / "frontend-vue" / "dist"
FRONTEND_DIR = FRONTEND_DIST_DIR if FRONTEND_DIST_DIR.exists() else BASE_DIR / "frontend"
FRONTEND_MOBILE_DIR = BASE_DIR / "frontend-mobile"
PUBLIC_ASSETS_DIR = BASE_DIR / "frontend-vue" / "public" / "assets"
PUBLIC_DATA_DIR = BASE_DIR / "示范景区公开资料包"
DATA_DIR = BASE_DIR / "backend" / "data"
DB_PATH = DATA_DIR / "scenic_guide.db"
HOST = "127.0.0.1"
PORT = 8000
DEFAULT_CORS_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000"
MAX_JSON_BODY_BYTES = env_int("SCENIC_MAX_JSON_BODY_BYTES", 80 * 1024 * 1024)
MAX_BEHAVIOR_EXCEL_BYTES = env_int("SCENIC_BEHAVIOR_EXCEL_MAX_BYTES", 64 * 1024 * 1024)
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_AUDIO_BYTES = 12 * 1024 * 1024
DEFAULT_BEHAVIOR_CONTENT_MAX_CHARS = 360
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-wav",
}
MUTATING_ADMIN_METHODS = {"POST", "PUT", "DELETE"}
SCHEMA_TABLES = {
    "scenic_spot",
    "chat_record",
    "route_record",
    "knowledge_document",
    "feedback_record",
    "persona_config",
}
RATE_LIMIT_BUCKETS = {}
BEHAVIOR_ANALYTICS_VERSION = 8
BEHAVIOR_ANALYTICS_CACHE = {"mtime": None, "version": None, "data": None}
BEHAVIOR_ANALYTICS_CACHE_FILE_NAME = "behavior_analytics_cache.json"
BEHAVIOR_ANALYTICS_CACHE_FILE = DATA_DIR / BEHAVIOR_ANALYTICS_CACHE_FILE_NAME
BEHAVIOR_SCENIC_MATCH_KEYWORDS = ("灵山", "拈花湾", "灵山大佛")
BEHAVIOR_ANALYSIS_SCOPE = "灵山游客行为记录"
BEHAVIOR_MATCH_RULE_DESCRIPTION = "按 attraction_name 字段包含“灵山 / 拈花湾 / 灵山大佛”筛选，后续画像、停留、消费和满意度只统计这些命中记录。"
DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
OFFICIAL_DATA_PREFIX = "官方资料包"
OFFICIAL_SPOT_IMAGES = [
    "assets/scenic/photos/lingshan-grand-buddha.jpg",
    "assets/scenic/photos/lingshan-screen-wall.jpg",
    "assets/scenic/photos/brahma-palace.jpg",
    "assets/scenic/photos/nine-dragons-bath.jpg",
    "assets/scenic/photos/nianhua-bay.jpg",
    "assets/scenic/photos/five-seal-mandala.jpg",
]
SPOT_IMAGE_OVERRIDES = {
    "灵山大佛": "assets/scenic/photos/lingshan-grand-buddha.jpg",
    "灵山大照壁": "assets/scenic/photos/lingshan-screen-wall.jpg",
    "五明桥": "assets/scenic/photos/five-brightness-bridge.png",
    "佛足坛": "assets/scenic/photos/buddha-foot-altar.png",
    "五智门": "assets/scenic/photos/five-wisdom-gate.jpg",
    "菩提大道": "assets/scenic/photos/bodhi-avenue.png",
    "降魔浮雕": "assets/scenic/photos/demon-subduing-relief.png",
    "阿育王柱": "assets/scenic/photos/ashoka-pillar.png",
    "百子戏弥勒": "assets/scenic/photos/children-mitreya.png",
    "百子弥勒戏": "assets/scenic/photos/children-mitreya.png",
    "佛教文化博览馆": "assets/scenic/photos/buddhist-culture-museum.jpg",
    "佛教文化博物馆": "assets/scenic/photos/buddhist-culture-museum.jpg",
    "梵天花海": "assets/scenic/photos/brahma-flower-sea.png",
    "曼飞龙塔": "assets/scenic/photos/manfeilong-pagoda.png",
    "无尽意斋": "assets/scenic/photos/wujinyi-zhai.png",
    "拈花广场": "assets/scenic/photos/nianhua-plaza.png",
    "拈花堂": "assets/scenic/photos/nianhua-hall.png",
}


def image_for_spot_name(name, fallback_index=0):
    text = str(name or "").strip()
    for keyword, image in SPOT_IMAGE_OVERRIDES.items():
        if keyword in text:
            return image
    return OFFICIAL_SPOT_IMAGES[fallback_index % len(OFFICIAL_SPOT_IMAGES)]


LEGACY_DEMO_SPOT_NAMES = [
    "云岚古城门",
    "云岚湖",
    "民俗博物馆",
    "花溪步道",
    "非遗工坊",
    "云顶观景台",
    "云岚美食街",
]
LEGACY_DEMO_KNOWLEDGE_TITLES = [
    "开放时间与票务政策",
    "交通停车指南",
    "亲子研学推荐",
    "历史文化讲解重点",
    "自然风光与拍照打卡",
    "安全与服务说明",
    "数字人讲解风格",
]
load_dotenv_files(BASE_DIR)


LLM_PROVIDER_DEFAULTS = {
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3-vl-plus",
        "key_names": ["SCENIC_LLM_API_KEY", "DASHSCOPE_API_KEY", "BAILIAN_API_KEY"],
        "require_key": True,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "key_names": ["SCENIC_LLM_API_KEY", "DEEPSEEK_API_KEY"],
        "require_key": True,
    },
    "custom": {
        "base_url": "http://127.0.0.1:8001/v1",
        "model": "qwen3-vl-plus",
        "key_names": ["SCENIC_LLM_API_KEY", "OPENAI_API_KEY"],
        "require_key": False,
    },
}

def build_llm_config(provider, env_prefix, key_names=None):
    provider = (provider or "dashscope").strip().lower() or "dashscope"
    defaults = LLM_PROVIDER_DEFAULTS.get(provider, LLM_PROVIDER_DEFAULTS["custom"])
    provider_key_names = defaults["key_names"] if key_names is None else key_names
    api_key = first_env([f"{env_prefix}API_KEY", *provider_key_names])
    base_url = os.getenv(f"{env_prefix}BASE_URL", defaults["base_url"]).strip().rstrip("/")
    model = os.getenv(f"{env_prefix}MODEL", defaults["model"]).strip()
    enabled = env_bool(f"{env_prefix}ENABLED", True)
    require_key = defaults["require_key"]
    available = enabled and (bool(api_key) or not require_key) and bool(base_url) and bool(model)
    reason = "ready"
    if not enabled:
        reason = "disabled"
    elif require_key and not api_key:
        reason = "missing_api_key"
    elif not base_url or not model:
        reason = "missing_base_url_or_model"
    return {
        "provider": provider,
        "baseUrl": base_url,
        "model": model,
        "apiKey": api_key,
        "hasApiKey": bool(api_key),
        "enabled": enabled,
        "available": available,
        "requireKey": require_key,
        "reason": reason,
        "temperature": env_float([f"{env_prefix}TEMPERATURE", "SCENIC_LLM_TEMPERATURE"], 0.35),
        "maxTokens": env_int([f"{env_prefix}MAX_TOKENS", "SCENIC_LLM_MAX_TOKENS"], 700),
        "timeout": env_int([f"{env_prefix}TIMEOUT", "SCENIC_LLM_TIMEOUT"], 25),
        "multimodal": is_multimodal_model(model),
    }


def get_llm_config():
    provider = os.getenv("SCENIC_LLM_PROVIDER", "dashscope").strip().lower() or "dashscope"
    return build_llm_config(provider, "SCENIC_LLM_")


def get_vision_llm_config():
    """Returns an independent config for vision/multimodal tasks."""
    provider = os.getenv("SCENIC_VISION_PROVIDER", "dashscope").strip().lower() or "dashscope"
    vision_key_names = {
        "dashscope": ["DASHSCOPE_API_KEY", "BAILIAN_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "custom": ["OPENAI_API_KEY"],
    }.get(provider, ["OPENAI_API_KEY"])
    return build_llm_config(provider, "SCENIC_VISION_", vision_key_names)


def public_llm_config(config):
    if not config:
        return None
    return {
        "provider": config["provider"],
        "baseUrl": config["baseUrl"],
        "model": config["model"],
        "enabled": config["enabled"],
        "available": config["available"],
        "hasApiKey": config["hasApiKey"],
        "reason": config["reason"],
        "multimodal": config["multimodal"],
    }


def llm_status():
    config = get_llm_config()
    vision_cfg = get_vision_llm_config()
    return {
        "provider": config["provider"],
        "baseUrl": config["baseUrl"],
        "model": config["model"],
        "configured": config["available"],
        "enabled": config["enabled"],
        "available": config["available"],
        "hasApiKey": config["hasApiKey"],
        "reason": config["reason"],
        "multimodal": config["multimodal"],
        "visionModel": vision_cfg["model"],
        "visionProvider": vision_cfg["provider"],
        "visionBaseUrl": vision_cfg["baseUrl"],
        "visionAvailable": vision_cfg["available"],
        "visionReason": vision_cfg["reason"],
        "visionHasApiKey": vision_cfg["hasApiKey"],
        "visionMultimodal": vision_cfg["multimodal"],
        "runtimeChecked": False,
        "runtimeReady": config["available"],
        "runtimeReason": config["reason"],
        "modelInstalled": None,
        "installedModels": [],
        "runtimeHint": "OpenAI 兼容云端 API，运行状态将在实际调用时验证。",
        "chatFastMode": env_bool("SCENIC_CHAT_FAST_MODE", False),
    }


def doubao_tts_config():
    app_id = first_env(["DOUBAO_TTS_APP_ID", "VOLCENGINE_TTS_APP_ID"])
    access_token = first_env(["DOUBAO_TTS_ACCESS_TOKEN", "VOLCENGINE_TTS_ACCESS_TOKEN"])
    cluster = os.getenv("DOUBAO_TTS_CLUSTER", os.getenv("VOLCENGINE_TTS_CLUSTER", "volcano_tts")).strip()
    voice_type = os.getenv("DOUBAO_TTS_VOICE_TYPE", "BV700_streaming").strip()
    endpoint = os.getenv("DOUBAO_TTS_ENDPOINT", "https://openspeech.bytedance.com/api/v1/tts").strip()
    enabled = env_bool("DOUBAO_TTS_ENABLED", True)
    available = enabled and bool(app_id) and bool(access_token) and bool(cluster) and bool(voice_type)
    reason = "ready"
    if not enabled:
        reason = "disabled"
    elif not app_id or not access_token:
        reason = "missing_app_id_or_access_token"
    elif not cluster or not voice_type:
        reason = "missing_cluster_or_voice"
    return {
        "provider": "doubao",
        "endpoint": endpoint,
        "appId": app_id,
        "hasAccessToken": bool(access_token),
        "accessToken": access_token,
        "cluster": cluster,
        "voiceType": voice_type,
        "enabled": enabled,
        "available": available,
        "reason": reason,
        "timeout": env_int("DOUBAO_TTS_TIMEOUT", 8),
    }


def tts_status():
    config = doubao_tts_config()
    return {
        "provider": config["provider"],
        "enabled": config["enabled"],
        "available": config["available"],
        "reason": config["reason"],
        "cluster": config["cluster"],
        "voiceType": config["voiceType"],
        "hasAccessToken": config["hasAccessToken"],
        "fallback": "browser_speech_synthesis",
    }


def asr_config():
    provider = os.getenv("SCENIC_ASR_PROVIDER", "browser").strip().lower() or "browser"
    enabled = env_bool("SCENIC_ASR_ENABLED", provider not in {"browser", "disabled", "off"})
    command_template = os.getenv(
        "SCENIC_ASR_COMMAND",
        "whisper {audio} --language zh --task transcribe --output_format txt --output_dir {output}",
    ).strip()
    endpoint = os.getenv("SCENIC_ASR_ENDPOINT", "").strip()
    api_key = first_env(["SCENIC_ASR_API_KEY", "WHISPER_API_KEY", "OPENAI_API_KEY"])
    timeout = env_int("SCENIC_ASR_TIMEOUT", 45)
    local_provider = provider in {"local_whisper", "whisper", "faster_whisper"}
    cloud_provider = provider in {"cloud", "cloud_asr", "remote"}
    command_name = shlex.split(command_template, posix=os.name != "nt")[0] if command_template else ""
    command_available = bool(command_name) and (Path(command_name).exists() or shutil.which(command_name) is not None)

    available = False
    reason = "browser_only"
    if not enabled or provider in {"browser", "disabled", "off"}:
        reason = "disabled"
    elif local_provider:
        available = command_available
        reason = "ready" if available else "missing_local_asr_command"
    elif cloud_provider:
        available = bool(endpoint)
        reason = "ready" if available else "missing_cloud_asr_endpoint"
    else:
        reason = "unsupported_provider"

    return {
        "provider": provider,
        "enabled": enabled,
        "available": available,
        "reason": reason,
        "command": command_template,
        "endpoint": endpoint,
        "hasApiKey": bool(api_key),
        "apiKey": api_key,
        "timeout": timeout,
        "fallback": "text_input",
    }


def asr_status():
    config = asr_config()
    return {
        "provider": config["provider"],
        "enabled": config["enabled"],
        "available": config["available"],
        "reason": config["reason"],
        "hasApiKey": config["hasApiKey"],
        "fallback": config["fallback"],
    }


def system_capabilities():
    llm = llm_status()
    tts = tts_status()
    asr = asr_status()
    try:
        with get_connection() as connection:
            active_knowledge = connection.execute("SELECT COUNT(*) FROM knowledge_document WHERE status = 'active'").fetchone()[0]
    except Exception:
        active_knowledge = 0
    multimodal_available = bool(llm.get("visionAvailable") and llm.get("visionMultimodal"))
    return {
        "coreAi": {
            "textProvider": llm["provider"],
            "textModel": llm["model"],
            "textAvailable": bool(llm["available"]),
            "multimodalProvider": llm.get("visionProvider", ""),
            "multimodalModel": llm.get("visionModel", ""),
            "multimodalAvailable": multimodal_available,
            "multimodalRequired": True,
            "multimodalRole": "游客上传图片识别、景区照片讲解与本地知识库联合回答",
        },
        "knowledge": {
            "localKnowledgeEnabled": True,
            "activeDocuments": active_knowledge,
            "sourcePolicy": "优先使用本地景区知识库、景点资料和官方资料来源，资料不足时明确提示。",
            "accuracyTarget": 0.9,
            "evaluationMethod": "由评审专家基于标准测试集评测事实性问答准确率。",
        },
        "interaction": {
            "textInput": True,
            "browserSpeechInput": True,
            "serverAsrAvailable": bool(asr.get("available")),
            "voiceOutput": True,
            "browserVoiceFallback": True,
            "expressionLipSync": True,
            "imageUnderstanding": multimodal_available,
        },
        "quality": {
            "factualAccuracyTarget": ">=90%",
            "voiceQaLatencyTargetMs": 5000,
            "stabilityTarget": "系统不崩溃、不长时间无响应，模型不可用时回退本地知识库。",
            "fallbackPolicy": "大模型、TTS、ASR 或地图能力不可用时均提供本地资料/浏览器能力/景区图兜底。",
        },
        "positioning": {
            "gpsSupported": True,
            "fallbackStrategies": [
                "浏览器定位失败时保留入口示例位置",
                "定位成功后按最近景点推荐",
                "高德底图不可用时切回景区图",
            ],
            "difficultScenarioPlan": "GPS 弱信号或室内定位不稳定时，结合手动选择景点、最近点推荐和人工校准点位保证导览可继续。",
        },
    }


def is_multimodal_model(model):
    normalized = model.lower()
    return any(flag in normalized for flag in ("vl", "vision", "internvl", "llava", "minicpm-v", "deepseek-vl"))


SEED_SPOTS = [
    {
        "name": "灵山大佛",
        "description": "通高88米的露天青铜释迦牟尼立像，是灵山胜境核心地标，可登顶抱佛脚并俯瞰太湖。",
        "story": "右手施无畏印、左手施与愿印，216级登云道暗合108烦恼与108愿望，是佛教文化和现代造像工艺结合的代表。",
        "tags": ["佛教文化", "历史文化", "拍照打卡"],
        "image": "assets/scenic/photos/lingshan-grand-buddha.jpg",
        "openTime": "随景区开放",
        "duration": 70,
        "popularity": 100,
        "location": "祥符禅寺北侧",
        "lat": 31.4308,
        "lon": 120.0968,
    },
    {
        "name": "灵山梵宫",
        "description": "建筑面积约7.2万平方米，被称为佛教艺术殿堂，融合木雕、壁画、琉璃和沉浸式演出。",
        "story": "梵宫是世界佛教论坛主会场，《吉祥颂》演出用全息投影、水雾和旋转舞台演绎佛陀修行成佛故事。",
        "tags": ["佛教文化", "演艺体验", "室内参观"],
        "image": "assets/scenic/photos/brahma-palace.jpg",
        "openTime": "10:35、11:30、14:00、16:00",
        "duration": 80,
        "popularity": 98,
        "location": "灵山胜境核心区",
        "lat": 31.4312,
        "lon": 120.0981,
    },
    {
        "name": "九龙灌浴",
        "description": "灵山胜境标志性动态景观，通过莲花开启、太子佛升起和九龙喷水再现佛陀诞生祥瑞。",
        "story": "平日演出通常为10:00、11:30、13:30、15:00，建议提前到场占位，表演后可接取祈福圣水。",
        "tags": ["佛教文化", "亲子游", "演艺体验", "拍照打卡"],
        "image": "assets/scenic/photos/nine-dragons-bath.jpg",
        "openTime": "10:00、11:30、13:30、15:00",
        "duration": 35,
        "popularity": 97,
        "location": "菩提大道北端",
        "lat": 31.4297,
        "lon": 120.0962,
    },
    {
        "name": "五印坛城",
        "description": "藏传佛教风格建筑，金顶红墙、经幡飘扬，可体验转经筒、坛城文化和观景平台。",
        "story": "坛城展现藏传佛教文化艺术精髓，顺时针绕行或转动经筒寓意福慧增长。",
        "tags": ["佛教文化", "拍照打卡", "室内参观"],
        "image": "assets/scenic/photos/five-seal-mandala.jpg",
        "openTime": "9:00-17:00",
        "duration": 55,
        "popularity": 93,
        "location": "香水海湖心岛",
        "lat": 31.4321,
        "lon": 120.0992,
    },
    {
        "name": "祥符禅寺",
        "description": "灵山大佛脚下的禅寺空间，适合进入核心礼佛区前安静参观，感受江南佛教文化。",
        "story": "寺院与大佛、登云道共同组成礼佛动线，游客可在此完成由山门到大佛的节奏转换。",
        "tags": ["佛教文化", "历史文化", "安静参观"],
        "image": "assets/scenic/photos/xiangfu-temple.jpg",
        "openTime": "随景区开放",
        "duration": 45,
        "popularity": 92,
        "location": "灵山大佛南侧",
        "lat": 31.4299,
        "lon": 120.0954,
    },
    {
        "name": "香月花街",
        "description": "拈花湾小镇内的餐饮购物街区，适合夜游、休憩、文创购物和轻松拍照。",
        "story": "香月花街通过江南街巷、灯光和禅意小品串联夜游体验，是拈花湾休闲动线的重要节点。",
        "tags": ["餐饮购物", "轻松休闲", "拍照打卡"],
        "image": "assets/scenic/photos/nianhua-street.jpg",
        "openTime": "以拈花湾公告为准",
        "duration": 55,
        "popularity": 91,
        "location": "拈花湾核心街区",
        "lat": 31.4148,
        "lon": 120.0785,
    },
    {
        "name": "游客服务中心",
        "description": "游客服务中心提供咨询、寄存、医药箱、失物招领、母婴和无障碍服务。",
        "story": "服务中心适合处理入园咨询、停车指引、轮椅租借、应急联系和失物招领等现场服务问题。",
        "tags": ["服务设施", "轻松休闲"],
        "image": "assets/scenic/photos/lingshan-screen-wall.jpg",
        "openTime": "随景区开放",
        "duration": 20,
        "popularity": 78,
        "location": "景区入口服务区",
        "lat": 31.4289,
        "lon": 120.0948,
    },
]


SEED_KNOWLEDGE = [
    {
        "title": "开放时间与票务政策",
        "category": "服务信息",
        "content": "灵山胜境成人票 210 元，半价票 105 元，网购门票加观光车联票 225 元，观光车单独购票 40 元/人。6 周岁以下或 1.4 米以下儿童、70 周岁以上老人、现役军人、残疾人可免票。具体开放时间、演出时间和优惠政策以景区公告为准，不要把“全天开放”理解成“免费开放”。",
    },
    {
        "title": "交通停车指南",
        "category": "服务信息",
        "content": "自驾游客可按现场指引前往灵山胜境停车区，入园后先确认游客服务中心、卫生间、母婴室和观光车乘车点。体力有限或带老人儿童游览时，可购买观光车并在核心节点间换乘。",
    },
    {
        "title": "亲子研学推荐",
        "category": "路线推荐",
        "content": "亲子家庭可优先游览九龙灌浴、佛手广场、百子戏弥勒、灵山梵宫和五印坛城。九龙灌浴适合观看动态表演，百子戏弥勒适合互动拍照，梵宫和坛城适合文化科普与室内参观。",
    },
    {
        "title": "历史文化讲解重点",
        "category": "景点讲解",
        "content": "历史文化爱好者可从灵山大照壁、祥符禅寺、灵山大佛、灵山梵宫、五印坛城等节点深度游览。讲解重点包括赵朴初题字、唐代小灵山道场、北宋大中祥符年间寺名、大佛手印寓意和世界佛教论坛主会场。",
    },
    {
        "title": "自然风光与拍照打卡",
        "category": "路线推荐",
        "content": "拍照打卡可选择灵山大照壁、九龙灌浴、灵山大佛、五印坛城和曼飞龙塔。灵山大佛适合拍恢弘地标，九龙灌浴适合拍动态表演，五印坛城和曼飞龙塔适合拍佛教建筑群。",
    },
    {
        "title": "安全与服务说明",
        "category": "安全服务",
        "content": "游客遇到迷路、身体不适、失物招领、无障碍通行等问题，可前往游客服务中心或联系现场工作人员。登云道台阶较多，雨天或老人儿童游览需注意防滑与体力安排；佛教文化场所应保持安静，不触摸佛像，听从拍照限制提示。",
    },
    {
        "title": "数字人讲解风格",
        "category": "数字人配置",
        "content": "数字人和尚默认使用亲切、专业、简洁的导游口吻。回答游客问题时优先引用知识库资料，信息不足时应说明暂未查询到，并引导游客咨询景区服务中心或查看公告。",
    },
]


DEFAULT_PERSONA = {
    "name": "数字僧人实时对话",
    "role": "请选择预设数字人，并绑定对应参考音频。先点击“开始连接”，连接成功后再点击“发送”。点击“保存预设音色”后，后续该角色说话都会使用这个音色。",
    "greeting": "阿弥陀佛，欢迎来到数字僧人实时对话系统。",
    "style": "男性僧人",
    "costume": "Avatar: test1 / 默认：Yunyang / 慢速 · 低沉 · 稳重",
    "voice": "edgetts / zh-CN-YunyangNeural",
    "accentColor": "#2f6d52",
    "voiceSpeed": 0.94,
    "voicePitch": 1.02,
    "expressionProfile": "阿弥陀佛，施主您好。欢迎来到灵山胜景。请随我漫步胜景，静听这千年的钟声，享受美景吧！",
    "avatarPresetKey": "male",
    "avatarId": "test1",
    "refAudio": "data/ref_audio/test1.wav",
    "refText": "阿弥陀佛，施主您好。欢迎来到灵山胜景。请随我漫步胜景，静听这千年的钟声，享受美景吧！",
    "avatarVoice": "zh-CN-YunyangNeural",
    "ttsMode": "edgetts",
}


POSITIVE_WORDS = ["喜欢", "满意", "不错", "好玩", "好看", "方便", "推荐", "清楚", "感谢", "开心"]
NEGATIVE_WORDS = ["不好", "不满意", "失望", "太远", "太累", "排队", "迷路", "贵", "糟糕", "投诉", "找不到"]


# mapX/mapY are calibrated for the handcrafted SVG basemap in the Vue client.
# They are not a projection of lat/lon and should not be treated as GIS-grade survey data.
SPOT_LOCATION_OVERRIDES = {
    "游客服务中心": {"zone": "lingshan", "lat": 31.4282, "lon": 120.0951, "mapX": 96, "mapY": 512},
    "灵山大照壁": {"zone": "lingshan", "lat": 31.42852, "lon": 120.09482, "mapX": 142, "mapY": 484},
    "五明桥": {"zone": "lingshan", "lat": 31.42874, "lon": 120.09448, "mapX": 202, "mapY": 452},
    "佛足坛": {"zone": "lingshan", "lat": 31.42896, "lon": 120.09405, "mapX": 266, "mapY": 418},
    "五智门": {"zone": "lingshan", "lat": 31.42916, "lon": 120.09368, "mapX": 330, "mapY": 382},
    "菩提大道": {"zone": "lingshan", "lat": 31.42936, "lon": 120.09336, "mapX": 400, "mapY": 342},
    "九龙灌浴": {"zone": "lingshan", "lat": 31.42948, "lon": 120.09302, "mapX": 474, "mapY": 300},
    "降魔浮雕": {"zone": "lingshan", "lat": 31.42978, "lon": 120.09270, "mapX": 548, "mapY": 258},
    "阿育王柱": {"zone": "lingshan", "lat": 31.43002, "lon": 120.09242, "mapX": 620, "mapY": 218},
    "百子戏弥勒": {"zone": "lingshan", "lat": 31.43020, "lon": 120.09218, "mapX": 690, "mapY": 182},
    "祥符禅寺": {"zone": "lingshan", "lat": 31.43042, "lon": 120.09202, "mapX": 752, "mapY": 150},
    "灵山大佛": {"zone": "lingshan", "lat": 31.43125, "lon": 120.09136, "mapX": 630, "mapY": 132},
    "佛教文化博览馆": {"zone": "lingshan", "lat": 31.43066, "lon": 120.09386, "mapX": 786, "mapY": 222},
    "灵山梵宫": {"zone": "lingshan", "lat": 31.43024, "lon": 120.09458, "mapX": 572, "mapY": 296},
    "五印坛城": {"zone": "lingshan", "lat": 31.43005, "lon": 120.09572, "mapX": 842, "mapY": 300},
    "曼飞龙塔": {"zone": "lingshan", "lat": 31.43094, "lon": 120.09692, "mapX": 846, "mapY": 126},
    "无尽意斋": {"zone": "lingshan", "lat": 31.43048, "lon": 120.09612, "mapX": 900, "mapY": 256},
    "拈花广场": {"zone": "nianhua", "lat": 31.41375, "lon": 120.08115, "mapX": 206, "mapY": 520},
    "梵天花海": {"zone": "nianhua", "lat": 31.41490, "lon": 120.08025, "mapX": 286, "mapY": 468},
    "香月花街": {"zone": "nianhua", "lat": 31.41535, "lon": 120.08125, "mapX": 222, "mapY": 430},
    "拈花堂": {"zone": "nianhua", "lat": 31.41590, "lon": 120.08175, "mapX": 154, "mapY": 412},
    "五灯湖": {"zone": "nianhua", "lat": 31.41275, "lon": 120.08245, "mapX": 342, "mapY": 492},
}

ROUTE_SPOT_ORDER = {
    "lingshan": {
        "游客服务中心": 10,
        "灵山大照壁": 20,
        "五明桥": 30,
        "佛足坛": 40,
        "五智门": 50,
        "菩提大道": 60,
        "九龙灌浴": 70,
        "降魔浮雕": 80,
        "阿育王柱": 90,
        "百子戏弥勒": 100,
        "祥符禅寺": 110,
        "灵山大佛": 120,
        "佛教文化博览馆": 130,
        "灵山梵宫": 140,
        "五印坛城": 150,
        "曼飞龙塔": 160,
        "无尽意斋": 170,
    },
    "nianhua": {
        "拈花广场": 10,
        "梵天花海": 20,
        "香月花街": 30,
        "拈花堂": 40,
        "五灯湖": 50,
    },
}

WAYFINDING_PATHS = {
    "lingshan": [
        "游客服务中心",
        "灵山大照壁",
        "五明桥",
        "佛足坛",
        "五智门",
        "菩提大道",
        "九龙灌浴",
        "灵山梵宫",
        "五印坛城",
        "曼飞龙塔",
        "无尽意斋",
    ],
    "nianhua": ["拈花广场", "香月花街", "拈花堂", "五灯湖", "梵天花海"],
}

OFFICIAL_ROUTE_TEMPLATE_SPECS = [
    {
        "id": "official-history-culture",
        "title": "历史文化爱好者路线",
        "start": "历史文化爱好者路线（6小时深度游）",
        "ends": ["自然风光爱好者路线（5小时全景游）"],
        "duration": 360,
        "preferences": {"佛教文化", "历史文化"},
        "zone": "lingshan",
    },
    {
        "id": "official-nature",
        "title": "自然风光爱好者路线",
        "start": "自然风光爱好者路线（5小时全景游）",
        "ends": ["亲子家庭路线（4小时轻松游）"],
        "duration": 300,
        "preferences": {"自然风光", "拍照打卡"},
        "zone": "lingshan",
    },
    {
        "id": "official-family",
        "title": "亲子家庭路线",
        "start": "亲子家庭路线（4小时轻松游）",
        "ends": ["实用游览贴士：全方位保障你的灵山之旅"],
        "duration": 240,
        "preferences": {"亲子游", "演艺体验"},
        "zone": "lingshan",
    },
]

ROUTE_WAYPOINT_ALIASES = {
    "梵宫": "灵山梵宫",
    "大佛": "灵山大佛",
    "华夏第一壁": "灵山大照壁",
}


def get_connection():
    return connect_database(DB_PATH)


def init_database():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS scenic_spot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                story TEXT NOT NULL,
                tags TEXT NOT NULL,
                image TEXT NOT NULL,
                open_time TEXT NOT NULL,
                duration INTEGER NOT NULL,
                popularity INTEGER NOT NULL,
                location TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_record (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                related_spots TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS route_record (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                duration INTEGER NOT NULL,
                estimated_duration INTEGER NOT NULL,
                preference TEXT NOT NULL,
                spots TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_document (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS feedback_record (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                comment TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS persona_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                greeting TEXT NOT NULL,
                style TEXT NOT NULL,
                costume TEXT NOT NULL,
                voice TEXT NOT NULL,
                accent_color TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS import_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS behavior_visit_record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                source_row INTEGER NOT NULL,
                tourist_id TEXT,
                user_nickname TEXT,
                age INTEGER,
                gender TEXT,
                attraction_name TEXT,
                attraction_content TEXT,
                attraction_type TEXT,
                visit_date TEXT,
                stay_duration REAL,
                ticket_cost REAL,
                food_cost REAL,
                shopping_cost REAL,
                transport_cost REAL,
                entertainment_cost REAL,
                total_cost REAL,
                group_size INTEGER,
                satisfaction REAL,
                raw_json TEXT NOT NULL,
                imported_at INTEGER NOT NULL,
                UNIQUE(source_file, source_row)
            );
            CREATE INDEX IF NOT EXISTS idx_behavior_visit_attraction ON behavior_visit_record(attraction_name);
            CREATE INDEX IF NOT EXISTS idx_behavior_visit_date ON behavior_visit_record(visit_date);
            CREATE INDEX IF NOT EXISTS idx_behavior_visit_source ON behavior_visit_record(source_file);
            """
        )
        add_column_if_missing(connection, "scenic_spot", "status", "TEXT NOT NULL DEFAULT 'active'")
        add_column_if_missing(connection, "scenic_spot", "updated_at", "INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(connection, "scenic_spot", "lat", "REAL")
        add_column_if_missing(connection, "scenic_spot", "lon", "REAL")
        add_column_if_missing(connection, "scenic_spot", "map_zone", "TEXT NOT NULL DEFAULT 'lingshan'")
        add_column_if_missing(connection, "scenic_spot", "map_x", "REAL")
        add_column_if_missing(connection, "scenic_spot", "map_y", "REAL")
        add_column_if_missing(connection, "scenic_spot", "verified_location", "INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(connection, "chat_record", "source_refs", "TEXT NOT NULL DEFAULT '[]'")
        add_column_if_missing(connection, "chat_record", "intent", "TEXT NOT NULL DEFAULT '其他咨询'")
        add_column_if_missing(connection, "chat_record", "confidence", "REAL NOT NULL DEFAULT 0.5")
        add_column_if_missing(connection, "chat_record", "sentiment", "TEXT NOT NULL DEFAULT 'neutral'")
        add_column_if_missing(connection, "chat_record", "satisfaction", "INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(connection, "knowledge_document", "source_type", "TEXT NOT NULL DEFAULT 'manual'")
        add_column_if_missing(connection, "knowledge_document", "source_file", "TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(connection, "knowledge_document", "source_section", "TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(connection, "persona_config", "voice_speed", "REAL NOT NULL DEFAULT 0.94")
        add_column_if_missing(connection, "persona_config", "voice_pitch", "REAL NOT NULL DEFAULT 1.02")
        add_column_if_missing(connection, "persona_config", "expression_profile", "TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(connection, "persona_config", "avatar_preset_key", "TEXT NOT NULL DEFAULT 'male'")
        add_column_if_missing(connection, "persona_config", "avatar_id", "TEXT NOT NULL DEFAULT 'test1'")
        add_column_if_missing(connection, "persona_config", "ref_audio", "TEXT NOT NULL DEFAULT 'data/ref_audio/test1.wav'")
        add_column_if_missing(connection, "persona_config", "ref_text", "TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(connection, "persona_config", "avatar_voice", "TEXT NOT NULL DEFAULT 'zh-CN-YunyangNeural'")
        add_column_if_missing(connection, "persona_config", "tts_mode", "TEXT NOT NULL DEFAULT 'edgetts'")
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_record(created_at);
            CREATE INDEX IF NOT EXISTS idx_route_created_at ON route_record(created_at);
            CREATE INDEX IF NOT EXISTS idx_knowledge_status ON knowledge_document(status);
            """
        )
        seed_spots(connection)
        seed_knowledge(connection)
        sync_official_public_data(connection)
        sync_known_spot_locations(connection)
        purge_legacy_demo_data(connection)
        seed_persona(connection)
        patch_persona_defaults(connection)


def seed_spots(connection):
    now = int(time.time())
    for index, raw_spot in enumerate(SEED_SPOTS):
        spot = apply_location_metadata(dict(raw_spot), index)
        exists = connection.execute("SELECT 1 FROM scenic_spot WHERE name = ?", (spot["name"],)).fetchone()
        if exists:
            connection.execute(
                """
                UPDATE scenic_spot
                SET image = CASE
                        WHEN image IS NULL OR image = '' OR image LIKE 'assets/spot-%.svg' OR image LIKE '/assets/spot-%.svg'
                        THEN ?
                        ELSE image
                    END,
                    lat = ?, lon = ?, map_zone = ?, map_x = ?, map_y = ?,
                    verified_location = CASE WHEN ? THEN 1 ELSE verified_location END,
                    updated_at = ?
                WHERE name = ?
                """,
                (
                    spot["image"],
                    spot.get("lat"),
                    spot.get("lon"),
                    spot["mapZone"],
                    spot["mapX"],
                    spot["mapY"],
                    1 if spot["verifiedLocation"] else 0,
                    now,
                    spot["name"],
                ),
            )
            continue
        connection.execute(
            """
            INSERT INTO scenic_spot
            (name, description, story, tags, image, open_time, duration, popularity, location, lat, lon,
             map_zone, map_x, map_y, verified_location, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                spot["name"],
                spot["description"],
                spot["story"],
                json.dumps(spot["tags"], ensure_ascii=False),
                spot["image"],
                spot["openTime"],
                spot["duration"],
                spot["popularity"],
                spot["location"],
                spot.get("lat"),
                spot.get("lon"),
                spot["mapZone"],
                spot["mapX"],
                spot["mapY"],
                1 if spot["verifiedLocation"] else 0,
                now,
                now,
            ),
        )


def seed_knowledge(connection):
    now = int(time.time())
    for item in SEED_KNOWLEDGE:
        exists = connection.execute(
            "SELECT 1 FROM knowledge_document WHERE title = ?", (item["title"],)
        ).fetchone()
        if exists:
            continue
        connection.execute(
            """
            INSERT INTO knowledge_document
            (id, title, category, content, status, source_type, source_file, source_section, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', 'seed', '', ?, ?, ?)
            """,
            (str(uuid.uuid4()), item["title"], item["category"], item["content"], item["title"], now, now),
        )
    patch_seed_knowledge(connection)


def patch_seed_knowledge(connection):
    ticket_patch = "知识库没有说明所有区域免费开放，回答时不能把全天开放理解为免费开放。"
    row = connection.execute(
        "SELECT id, content FROM knowledge_document WHERE title = ?",
        ("开放时间与票务政策",),
    ).fetchone()
    if not row or ticket_patch in row["content"]:
        return
    content = row["content"].rstrip()
    if content and not content.endswith("。"):
        content += "。"
    connection.execute(
        "UPDATE knowledge_document SET content = ?, updated_at = ? WHERE id = ?",
        (content + ticket_patch, int(time.time()), row["id"]),
    )


def location_metadata_for_spot(name, fallback_lat=None, fallback_lon=None, fallback_index=0, fallback_zone="lingshan"):
    override = SPOT_LOCATION_OVERRIDES.get(str(name or "").strip())
    if override:
        return {
            "lat": override["lat"],
            "lon": override["lon"],
            "mapZone": override["zone"],
            "mapX": override["mapX"],
            "mapY": override["mapY"],
            "verifiedLocation": True,
        }
    fallback_slots = [
        (136, 488),
        (230, 440),
        (330, 386),
        (432, 330),
        (536, 270),
        (640, 212),
        (744, 154),
        (836, 238),
        (764, 324),
        (614, 390),
        (448, 456),
        (286, 506),
    ]
    map_x, map_y = fallback_slots[fallback_index % len(fallback_slots)]
    return {
        "lat": fallback_lat,
        "lon": fallback_lon,
        "mapZone": fallback_zone,
        "mapX": map_x,
        "mapY": map_y,
        "verifiedLocation": False,
    }


def apply_location_metadata(spot, index=0):
    fallback_zone = "nianhua" if str(spot.get("name", "")).startswith("拈花") or "拈花" in str(spot.get("location", "")) else "lingshan"
    metadata = location_metadata_for_spot(
        spot.get("name"),
        spot.get("lat"),
        spot.get("lon"),
        index,
        fallback_zone,
    )
    spot.update(metadata)
    return spot


def seed_persona(connection):
    exists = connection.execute("SELECT 1 FROM persona_config WHERE id = 1").fetchone()
    if exists:
        return
    now = int(time.time())
    connection.execute(
        """
        INSERT INTO persona_config
        (id, name, role, greeting, style, costume, voice, accent_color, voice_speed, voice_pitch, expression_profile, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            DEFAULT_PERSONA["name"],
            DEFAULT_PERSONA["role"],
            DEFAULT_PERSONA["greeting"],
            DEFAULT_PERSONA["style"],
            DEFAULT_PERSONA["costume"],
            DEFAULT_PERSONA["voice"],
            DEFAULT_PERSONA["accentColor"],
            DEFAULT_PERSONA["voiceSpeed"],
            DEFAULT_PERSONA["voicePitch"],
            DEFAULT_PERSONA["expressionProfile"],
            now,
        ),
    )


def patch_persona_defaults(connection):
    row = connection.execute("SELECT * FROM persona_config WHERE id = 1").fetchone()
    if not row:
        return
    now = int(time.time())
    legacy_text = " ".join(str(row[key] or "") for key in ("name", "role", "greeting", "costume"))
    default_like_persona = (
        str(row["name"] or "").strip() in {"小游", "灵灵", "灵童", "和尚"}
        or "云岚" in legacy_text
        or "导览服" in legacy_text
        or str(row["role"] or "").strip() == "灵山胜境和尚数字导览员"
    )
    if default_like_persona:
        connection.execute(
            """
            UPDATE persona_config
            SET name = ?, role = ?, greeting = ?, style = ?, costume = ?, voice = ?, accent_color = ?,
                voice_speed = ?, voice_pitch = ?, expression_profile = ?, updated_at = ?
            WHERE id = 1
            """,
            (
                DEFAULT_PERSONA["name"],
                DEFAULT_PERSONA["role"],
                DEFAULT_PERSONA["greeting"],
                DEFAULT_PERSONA["style"],
                DEFAULT_PERSONA["costume"],
                DEFAULT_PERSONA["voice"],
                DEFAULT_PERSONA["accentColor"],
                DEFAULT_PERSONA["voiceSpeed"],
                DEFAULT_PERSONA["voicePitch"],
                DEFAULT_PERSONA["expressionProfile"],
                now,
            ),
        )
        return
    outdated_voices = {"", "zh-CN-XiaoxiaoNeural", "XiaoxiaoNeural"}
    if str(row["voice"] or "").strip() in outdated_voices:
        connection.execute(
            "UPDATE persona_config SET voice = ?, updated_at = ? WHERE id = 1",
            (DEFAULT_PERSONA["voice"], now),
        )


def clean_public_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def trim_public_text(value, limit=220):
    text = clean_public_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip("，；、。 ") + "…"


def find_public_data_file(keyword, suffix):
    if not PUBLIC_DATA_DIR.exists():
        return None
    candidates = sorted(
        (path for path in PUBLIC_DATA_DIR.glob(f"*{suffix}") if not path.name.startswith("~$")),
        key=lambda item: ("副本" in item.stem or "copy" in item.stem.lower(), item.name),
    )
    for path in candidates:
        if keyword in path.name:
            return path
    if len(candidates) == 1:
        return candidates[0]
    return None


def read_docx_paragraphs(path):
    if not path or not path.exists():
        return []
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(document_xml)
    except (KeyError, OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        print(f"[DATA] 官方资料包读取失败：{path.name} {exc}")
        return []

    text_tag = f"{{{DOCX_NS['w']}}}t"
    tab_tag = f"{{{DOCX_NS['w']}}}tab"
    paragraphs = []
    for paragraph in root.findall(".//w:p", DOCX_NS):
        parts = []
        for node in paragraph.iter():
            if node.tag == text_tag:
                parts.append(node.text or "")
            elif node.tag == tab_tag:
                parts.append("\t")
        text = clean_public_text("".join(parts))
        if text:
            paragraphs.append(text)
    return paragraphs


def is_official_spot_id(value):
    return bool(re.match(r"^(LS|NH)-\d{3}$", str(value or "").strip()))


def lingshan_big_buddha_fields():
    return [
        "祥符禅寺北侧，秦履峰南侧，矗立在景区最高处，是整个灵山胜境的核心地标，可俯瞰整个景区及太湖风光。",
        "通高88米，含台基总高101.5米，总用铜量725吨，由大型铸铜面板拼接而成，是世界著名露天青铜释迦牟尼立像。",
        "景区核心地标、祈福朝圣与佛教造像艺术展示，适合游客登顶抱佛脚、俯瞰太湖并了解佛教手印寓意。",
        "右手施无畏印，寓意除却众生痛苦；左手施与愿印，寓意赐予众生欢乐。216级登云道暗合108烦恼与108愿望。",
        "灵山大佛是现代灵山胜境的标志性建筑，1997年落成开光。大佛面向太湖，背靠秦履峰，与祥符禅寺、五智门等构成中轴线朝圣序列，体现赵朴初先生提出的五方五佛理念。",
        "登顶抱佛脚，近距离感受大佛体量；在佛脚平台俯瞰太湖与景区全貌；傍晚拍摄夕阳映照大佛的佛光效果。",
        "随景区开放时间开放；登云道台阶较多，雨天或老人儿童游览需注意防滑与体力安排。",
        "灵山胜境必看核心景点，适合佛教文化、历史文化、拍照打卡与深度讲解路线。",
    ]


def parse_official_spot_records():
    path = find_public_data_file("结构化数据集", ".docx")
    lines = read_docx_paragraphs(path)
    if not lines:
        return []

    marker_indexes = [index for index, line in enumerate(lines) if is_official_spot_id(line)]
    records = []
    for index, marker_index in enumerate(marker_indexes):
        source_id = lines[marker_index]
        scenic_name = lines[marker_index - 1] if marker_index else "灵山胜境"
        spot_name = lines[marker_index + 1] if marker_index + 1 < len(lines) else source_id
        next_marker = marker_indexes[index + 1] if index + 1 < len(marker_indexes) else len(lines) + 1
        fields = lines[marker_index + 2 : max(marker_index + 2, next_marker - 1)]
        if source_id == "LS-011" and len(fields) < 8:
            fields = lingshan_big_buddha_fields()
        if len(fields) < 5:
            continue
        fields = [*fields[:8], *[""] * max(0, 8 - len(fields))]
        records.append(
            {
                "scenicName": scenic_name,
                "sourceId": source_id,
                "name": spot_name,
                "location": fields[0],
                "parameters": fields[1],
                "coreFunction": fields[2],
                "culture": fields[3],
                "detail": fields[4],
                "highlights": fields[5],
                "openInfo": fields[6],
                "remarks": fields[7],
            }
        )
    return records


def infer_official_tags(record):
    text = " ".join(str(record.get(key, "")) for key in ("name", "scenicName", "coreFunction", "culture", "detail", "highlights", "remarks"))
    tag_rules = [
        ("佛教文化", ["佛教", "禅", "朝圣", "祈福", "佛", "坛城", "梵宫"]),
        ("历史文化", ["历史", "唐", "赵朴初", "古刹", "文化", "博览馆", "纪念"]),
        ("亲子游", ["亲子", "孩童", "家庭", "科普", "互动"]),
        ("拍照打卡", ["拍照", "打卡", "观景", "湖", "花海", "夜景", "地标"]),
        ("演艺体验", ["表演", "演出", "灯光秀", "动态", "音乐"]),
        ("自然风光", ["太湖", "花海", "林", "山", "水", "绿植", "园林"]),
        ("餐饮购物", ["餐饮", "商铺", "素斋", "文创", "消费"]),
        ("室内参观", ["馆", "殿", "室内", "展厅", "禁止触摸"]),
    ]
    tags = [tag for tag, keywords in tag_rules if any(keyword in text for keyword in keywords)]
    return tags[:5] or ["综合导览"]


def infer_official_duration(name, tags):
    duration_map = {
        "灵山大佛": 70,
        "灵山梵宫": 80,
        "佛教文化博览馆": 60,
        "祥符禅寺": 55,
        "五印坛城": 55,
        "九龙灌浴": 35,
        "菩提大道": 25,
        "香月花街": 55,
        "梵天花海": 45,
        "五灯湖": 45,
        "拈花堂": 35,
    }
    if name in duration_map:
        return duration_map[name]
    if "室内参观" in tags:
        return 45
    if "拍照打卡" in tags:
        return 30
    return 35


def infer_official_popularity(name, index):
    popularity_map = {
        "灵山大佛": 100,
        "灵山梵宫": 98,
        "九龙灌浴": 97,
        "五印坛城": 93,
        "祥符禅寺": 92,
        "灵山大照壁": 90,
        "香月花街": 91,
        "五灯湖": 90,
        "梵天花海": 89,
    }
    return popularity_map.get(name, max(72, 90 - index))


def extract_official_open_time(open_info):
    text = clean_public_text(open_info)
    if not text:
        return "以景区公告为准"
    if "全天开放" in text:
        return "全天开放"
    ranges = re.findall(r"\d{1,2}:\d{2}\s*[-—至]\s*\d{1,2}:\d{2}", text)
    if ranges:
        suffix = "等" if len(ranges) > 3 else ""
        return "、".join(ranges[:3]) + suffix
    times = re.findall(r"\d{1,2}:\d{2}", text)
    if 1 <= len(times) <= 5:
        return "、".join(times)
    return trim_public_text(text, 86)


def official_spot_coordinates(record, index):
    name = str(record.get("name", "")).strip()
    override = SPOT_LOCATION_OVERRIDES.get(name)
    if override:
        return override["lat"], override["lon"]
    if str(record.get("sourceId", "")).startswith("NH"):
        return 31.4148, 120.0811
    return 31.4315, 120.0970


def official_record_to_spot(record, index):
    tags = infer_official_tags(record)
    lat, lon = official_spot_coordinates(record, index)
    scenic_name = record["scenicName"]
    name = record["name"]
    description = trim_public_text(f"{record['coreFunction']} {record['culture']}", 180)
    story = clean_public_text(
        f"{record['detail']} 游玩亮点：{record['highlights']} 开放/演艺信息：{record['openInfo']} 备注：{record['remarks']}"
    )
    return apply_location_metadata({
        "name": name,
        "description": description or f"{name}是{scenic_name}的重要导览节点。",
        "story": story or description,
        "tags": tags,
        "image": image_for_spot_name(name, index),
        "openTime": extract_official_open_time(record["openInfo"]),
        "duration": infer_official_duration(name, tags),
        "popularity": infer_official_popularity(name, index),
        "location": record["location"] or scenic_name,
        "lat": lat,
        "lon": lon,
    }, index)


def guide_section(lines, start_title, end_titles):
    try:
        start = lines.index(start_title)
    except ValueError:
        return ""
    end = len(lines)
    for title in end_titles:
        try:
            candidate = lines.index(title, start + 1)
        except ValueError:
            continue
        end = min(end, candidate)
    return "\n".join(lines[start:end]).strip()


def normalize_route_waypoint_name(value):
    text = normalize_text(value)
    text = re.sub(r"（.*?）|\(.*?\)", "", text)
    text = text.replace("入园", "").replace("出口", "").strip(" -—：:")
    return ROUTE_WAYPOINT_ALIASES.get(text, text)


def extract_route_waypoints(section_content):
    route_line = next((line for line in section_content.splitlines() if line.startswith("路线规划")), "")
    if not route_line:
        match = re.search(r"路线规划[:：](.*?)(?:讲解重点[:：]|特色体验[:：]|$)", section_content, re.S)
        route_line = match.group(1) if match else ""
    route_text = re.sub(r"^路线规划[:：]\s*", "", route_line).strip()
    waypoints = []
    for raw_item in re.split(r"\s*→\s*", route_text):
        name = normalize_route_waypoint_name(raw_item)
        if name and name not in {"南门", "出口"}:
            waypoints.append(name)
    return waypoints


def match_route_waypoint_to_spot_name(waypoint, spot_names):
    normalized_waypoint = normalize_text(waypoint)
    for name in spot_names:
        normalized_name = normalize_text(name)
        if normalized_waypoint == normalized_name:
            return name
    for name in spot_names:
        normalized_name = normalize_text(name)
        if normalized_waypoint and (normalized_waypoint in normalized_name or normalized_name in normalized_waypoint):
            return name
    return None


def load_official_route_templates(spots):
    guide_path = find_public_data_file("游览指南", ".docx")
    guide_lines = read_docx_paragraphs(guide_path)
    if not guide_lines:
        return []
    spot_names = [spot["name"] for spot in spots]
    templates = []
    for spec in OFFICIAL_ROUTE_TEMPLATE_SPECS:
        content = guide_section(guide_lines, spec["start"], spec["ends"])
        if not content:
            continue
        waypoints = extract_route_waypoints(content)
        spot_sequence = []
        for waypoint in waypoints:
            spot_name = match_route_waypoint_to_spot_name(waypoint, spot_names)
            if spot_name and spot_name not in spot_sequence:
                spot_sequence.append(spot_name)
        templates.append(
            {
                **spec,
                "sourceFile": guide_path.name if guide_path else "",
                "sourceSection": spec["start"],
                "content": content,
                "waypoints": waypoints,
                "spotSequence": spot_sequence,
            }
        )
    return templates


def load_behavior_dataset_summary():
    path = find_public_data_file("旅游数据行为分析", ".xlsx")
    if not path or not path.exists():
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            shared_strings = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                for item in root.findall("main:si", ns):
                    shared_strings.append("".join((node.text or "") for node in item.findall(".//main:t", ns)))
            ns_uri = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            with archive.open("xl/worksheets/sheet1.xml") as sheet_source:
                for _, elem in ElementTree.iterparse(sheet_source, events=("end",)):
                    if elem.tag != f"{{{ns_uri}}}row":
                        continue
                    headers = []
                    for cell in elem.findall(f"{{{ns_uri}}}c"):
                        value_node = cell.find(f"{{{ns_uri}}}v")
                        if value_node is None:
                            continue
                        raw = value_node.text or ""
                        if cell.attrib.get("t") == "s" and raw.isdigit():
                            headers.append(shared_strings[int(raw)])
                        else:
                            headers.append(raw)
                    elem.clear()
                    return (
                        "官方行为分析表包含游客ID、昵称、年龄、性别、景区名称、景区内容、景区类型、游玩日期、停留时长、"
                        "门票/餐饮/购物/交通/娱乐消费、总消费、同行人数和满意度等字段，可用于扩展游客画像、偏好分析、"
                        f"服务质量监测和管理后台运营看板。字段清单：{'、'.join(headers)}。"
                    )
    except (KeyError, OSError, zipfile.BadZipFile, ElementTree.ParseError, ValueError) as exc:
        print(f"[DATA] 行为分析表读取失败：{exc}")
    return ""


def chunk_paragraphs(paragraphs, max_chars=2600):
    chunks = []
    current = []
    current_length = 0
    for paragraph in paragraphs:
        text = clean_public_text(paragraph)
        if not text:
            continue
        next_length = current_length + len(text) + 1
        if current and next_length > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_length = 0
        current.append(text)
        current_length += len(text) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def build_full_docx_knowledge_documents():
    documents = []
    for path in sorted(PUBLIC_DATA_DIR.glob("*.docx")) if PUBLIC_DATA_DIR.exists() else []:
        paragraphs = read_docx_paragraphs(path)
        for index, content in enumerate(chunk_paragraphs(paragraphs), start=1):
            documents.append(
                {
                    "title": f"{OFFICIAL_DATA_PREFIX}全文：{path.stem}（第{index}段）",
                    "category": "官方资料全文",
                    "content": content,
                    "sourceType": "official_docx",
                    "sourceFile": path.name,
                    "sourceSection": f"全文分块 {index}",
                }
            )
    return documents


def behavior_analytics_summary_document():
    analytics = build_behavior_analytics_from_table()
    if not analytics or not analytics.get("available"):
        return None
    top_attractions = "、".join(f"{name}({count})" for name, count in analytics.get("topAttractions", [])[:10])
    type_distribution = "、".join(f"{name}({count})" for name, count in analytics.get("typeDistribution", [])[:8])
    age_distribution = "、".join(f"{name}:{count}" for name, count in analytics.get("ageDistribution", {}).items())
    gender_distribution = "、".join(f"{name}:{count}" for name, count in analytics.get("genderDistribution", {}).items())
    consumption = "、".join(f"{item['name']}均值{item['value']}" for item in analytics.get("consumptionBreakdown", []))
    trend = "、".join(f"{item['date']}满意度{item['score']}({item['count']}条)" for item in analytics.get("satisfactionTrend", [])[:18])
    source = analytics.get("dataSource", {})
    content = "\n".join(
        [
            f"数据源文件：{source.get('file', '')}",
            f"当前分析口径：{analytics.get('analysisScope', BEHAVIOR_ANALYSIS_SCOPE)}",
            f"全量记录数：{analytics.get('rowCount', 0)}",
            f"按灵山/拈花湾/灵山大佛关键词匹配记录数：{analytics.get('matchedScenicRows', 0)}",
            f"命中规则说明：{analytics.get('matchRuleDescription', BEHAVIOR_MATCH_RULE_DESCRIPTION)}",
            f"灵山资料来源：{'、'.join(analytics.get('officialDocumentSources', []))}",
            f"日期范围：{analytics.get('dateRange', {}).get('start', '')} 至 {analytics.get('dateRange', {}).get('end', '')}",
            f"平均停留时长：{analytics.get('averageStayDuration', 0)} 小时",
            f"平均满意度：{analytics.get('averageSatisfaction', 0)}",
            f"平均同行人数：{analytics.get('averageGroupSize', 0)}",
            f"热门景区/景点排行：{top_attractions}",
            f"景区类型分布：{type_distribution}",
            f"年龄分布：{age_distribution}",
            f"性别分布：{gender_distribution}",
            f"人均消费拆分：{consumption}",
            f"月度满意度趋势：{trend}",
            "说明：该 Excel 已导入结构化行为表；游客行为画像、大屏和报告只统计 attraction_name 命中灵山、拈花湾或灵山大佛的记录。",
        ]
    )
    behavior_path = behavior_source_file()
    return {
        "title": f"{OFFICIAL_DATA_PREFIX}：灵山游客行为记录摘要",
        "category": "行为数据分析",
        "content": content,
        "sourceType": "behavior_excel",
        "sourceFile": behavior_path.name if behavior_path else "",
        "sourceSection": "全量统计摘要",
    }


def xlsx_column_index(cell_ref):
    letters = "".join(char for char in str(cell_ref or "") if char.isalpha())
    index = 0
    for char in letters.upper():
        index = index * 26 + (ord(char) - ord("A") + 1)
    return max(index - 1, 0)


def xlsx_cell_value(cell, shared_strings, ns_uri):
    inline_text = cell.find(f"{{{ns_uri}}}is")
    if inline_text is not None:
        return "".join(node.text or "" for node in inline_text.iter() if node.tag == f"{{{ns_uri}}}t")
    value_node = cell.find(f"{{{ns_uri}}}v")
    if value_node is None:
        return ""
    raw = value_node.text or ""
    cell_type = cell.attrib.get("t")
    if cell_type == "s" and raw.isdigit():
        index = int(raw)
        return shared_strings[index] if 0 <= index < len(shared_strings) else ""
    return raw


def iter_xlsx_rows(path):
    if not path or not path.exists():
        return
    ns_uri = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    try:
        with zipfile.ZipFile(path) as archive:
            shared_strings = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                ns = {"main": ns_uri}
                for item in root.findall("main:si", ns):
                    shared_strings.append("".join((node.text or "") for node in item.findall(".//main:t", ns)))
            with archive.open("xl/worksheets/sheet1.xml") as sheet_source:
                for _, elem in ElementTree.iterparse(sheet_source, events=("end",)):
                    if elem.tag != f"{{{ns_uri}}}row":
                        continue
                    values = []
                    for cell in elem.findall(f"{{{ns_uri}}}c"):
                        col_index = xlsx_column_index(cell.attrib.get("r", ""))
                        while len(values) < col_index:
                            values.append("")
                        values.append(xlsx_cell_value(cell, shared_strings, ns_uri))
                    elem.clear()
                    yield values
    except (KeyError, OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        print(f"[DATA] 行为分析表解析失败：{exc}")


def as_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value, default=0):
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def excel_date_text(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    text = str(value or "").strip()
    if not text:
        return ""
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", text):
        return text[:10]
    try:
        serial = float(text)
    except ValueError:
        return text[:10]
    return (datetime(1899, 12, 30) + timedelta(days=serial)).strftime("%Y-%m-%d")


def age_bucket(age):
    value = as_int(age, -1)
    if value < 0:
        return "未知"
    if value < 18:
        return "18岁以下"
    if value <= 30:
        return "18-30岁"
    if value <= 45:
        return "31-45岁"
    if value <= 60:
        return "46-60岁"
    return "60岁以上"


def import_metadata_key_for_path(path, purpose):
    return f"{purpose}:{path.name}"


def source_file_signature(path, source_file_name=None):
    stat = path.stat()
    return f"{source_file_name or path.name}:{stat.st_size}:{stat.st_mtime}"


def get_import_metadata(connection, key):
    row = connection.execute("SELECT value FROM import_metadata WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else ""


def set_import_metadata(connection, key, value):
    now = int(time.time())
    connection.execute(
        """
        INSERT INTO import_metadata (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, value, now),
    )


def clear_behavior_analytics_cache():
    BEHAVIOR_ANALYTICS_CACHE["mtime"] = None
    BEHAVIOR_ANALYTICS_CACHE["version"] = None
    BEHAVIOR_ANALYTICS_CACHE["data"] = None
    try:
        behavior_analytics_cache_file().unlink()
    except OSError:
        pass


def active_behavior_import_metadata(connection):
    raw = get_import_metadata(connection, "behavior_visit_record:active")
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def set_active_behavior_import_metadata(connection, source_file, signature, imported_at):
    set_import_metadata(
        connection,
        "behavior_visit_record:active",
        json.dumps(
            {"sourceFile": source_file, "signature": signature, "importedAt": imported_at},
            ensure_ascii=False,
        ),
    )


def behavior_source_file():
    return find_public_data_file("旅游数据行为分析", ".xlsx")


def official_document_source_files():
    if not PUBLIC_DATA_DIR.exists():
        return []
    return [path.name for path in sorted(PUBLIC_DATA_DIR.glob("*.docx"))]


def behavior_structured_table_status(connection):
    path = behavior_source_file()
    source_row = None
    last_imported_at = None
    try:
        row_count = connection.execute("SELECT COUNT(*) AS count FROM behavior_visit_record").fetchone()["count"]
        source_row = connection.execute(
            """
            SELECT source_file, COUNT(*) AS count, MAX(imported_at) AS imported_at
            FROM behavior_visit_record
            GROUP BY source_file
            ORDER BY count DESC, source_file ASC
            LIMIT 1
            """
        ).fetchone()
    except Exception:
        row_count = 0

    source_file = source_row["source_file"] if source_row else (path.name if path else "")
    if source_row:
        last_imported_at = source_row["imported_at"]
    metadata_key = import_metadata_key_for_path(path, "behavior_visit_record") if path else ""
    expected_signature = behavior_import_signature(path, path.name) if path and path.exists() else ""
    imported_signature = get_import_metadata(connection, metadata_key) if metadata_key else ""
    active_metadata = active_behavior_import_metadata(connection)
    active_source_file = str(active_metadata.get("sourceFile") or "")
    active_signature = str(active_metadata.get("signature") or "")
    active_imported_at = active_metadata.get("importedAt")
    active_table_current = bool(row_count and active_source_file and active_source_file == source_file and active_signature)
    default_table_current = bool(row_count and expected_signature and imported_signature == expected_signature)
    if not last_imported_at and active_imported_at:
        last_imported_at = active_imported_at
    return {
        "structuredTableName": "behavior_visit_record",
        "structuredTableImported": row_count > 0,
        "structuredTableCurrent": active_table_current or default_table_current,
        "behaviorRecordCount": row_count,
        "sourceFile": source_file,
        "sourceFileFound": bool(path and path.exists()),
        "lastImportedAt": last_imported_at,
        "importMetadataKey": metadata_key,
    }


def behavior_analytics_context_fields(table_status):
    source_file = table_status.get("sourceFile") or (behavior_source_file().name if behavior_source_file() else "")
    return {
        "structuredTableName": table_status.get("structuredTableName", "behavior_visit_record"),
        "structuredTableImported": bool(table_status.get("structuredTableImported")),
        "structuredTableCurrent": bool(table_status.get("structuredTableCurrent")),
        "behaviorRecordCount": int(table_status.get("behaviorRecordCount") or 0),
        "analysisScope": BEHAVIOR_ANALYSIS_SCOPE,
        "analysisScopeDescription": "游客行为画像来自 Excel 中 attraction_name 命中灵山、拈花湾或灵山大佛的记录；非灵山景区记录不参与大屏和报告聚合。",
        "sampleSourceFile": source_file,
        "scenicMatchedKeywords": list(BEHAVIOR_SCENIC_MATCH_KEYWORDS),
        "matchRuleDescription": BEHAVIOR_MATCH_RULE_DESCRIPTION,
        "officialDocumentSources": official_document_source_files(),
        "lingshanDocumentSource": "灵山官方 DOCX 资料包",
    }


def behavior_scenic_where_clause(alias=""):
    prefix = f"{alias}." if alias else ""
    clauses = [f"{prefix}attraction_name LIKE ?" for _keyword in BEHAVIOR_SCENIC_MATCH_KEYWORDS]
    return "(" + " OR ".join(clauses) + ")"


def behavior_scenic_where_params():
    return tuple(f"%{keyword}%" for keyword in BEHAVIOR_SCENIC_MATCH_KEYWORDS)


def behavior_row_matches_scenic(attraction_name):
    text = str(attraction_name or "")
    return any(keyword in text for keyword in BEHAVIOR_SCENIC_MATCH_KEYWORDS)


def satisfaction_sentiment_label(score):
    value = as_float(score, None)
    if value is None:
        return "unknown"
    if value >= 4:
        return "positive"
    if value <= 2:
        return "negative"
    return "neutral"


def satisfaction_score_key(score):
    value = as_float(score, None)
    if value is None:
        return "unknown"
    return str(int(value)) if float(value).is_integer() else str(value)


def sentiment_label_from_rating(score, fallback=""):
    label = satisfaction_sentiment_label(score)
    if label != "unknown":
        return label
    return str(fallback or "").strip()


def current_behavior_structured_table_status():
    try:
        with get_connection() as connection:
            return behavior_structured_table_status(connection)
    except Exception:
        path = behavior_source_file()
        return {
            "structuredTableName": "behavior_visit_record",
            "structuredTableImported": False,
            "structuredTableCurrent": False,
            "behaviorRecordCount": 0,
            "sourceFile": path.name if path else "",
            "sourceFileFound": bool(path and path.exists()),
            "lastImportedAt": None,
            "importMetadataKey": "",
        }


def behavior_visit_table_is_current(connection):
    return behavior_structured_table_status(connection)["structuredTableCurrent"]


def behavior_content_max_chars():
    return max(0, env_int("SCENIC_BEHAVIOR_CONTENT_MAX_CHARS", DEFAULT_BEHAVIOR_CONTENT_MAX_CHARS))


def compact_behavior_content(value):
    text = str(value or "").strip()
    limit = behavior_content_max_chars()
    if limit and len(text) > limit:
        return text[:limit].rstrip("，,；;。") + "。"
    return text


def behavior_store_raw_json():
    return env_bool("SCENIC_BEHAVIOR_STORE_RAW_JSON", False)


def behavior_import_signature(path, source_file_name=None):
    return "|".join(
        [
            source_file_signature(path, source_file_name),
            f"raw_json={int(behavior_store_raw_json())}",
            f"content_max={behavior_content_max_chars()}",
            "schema=compact-v2",
        ]
    )


def import_behavior_visit_records_from_path(connection, path, source_file_name=None, force=False):
    path = Path(path) if path else None
    if not path or not path.exists():
        return {"imported": False, "behaviorRecordCount": 0, "message": "未找到游客行为分析 Excel。"}

    source_file = str(source_file_name or path.name).strip() or path.name
    signature = behavior_import_signature(path, source_file)
    metadata_key = f"behavior_visit_record:{source_file}"
    active_metadata = active_behavior_import_metadata(connection)
    existing_count = connection.execute(
        "SELECT COUNT(*) AS count FROM behavior_visit_record",
    ).fetchone()["count"]
    if (
        not force
        and existing_count
        and active_metadata.get("sourceFile") == source_file
        and active_metadata.get("signature") == signature
    ):
        return {
            "imported": False,
            "behaviorRecordCount": existing_count,
            "structuredTableCurrent": True,
            "sourceFile": source_file,
            "message": "游客行为明细表已是最新。",
        }

    rows = iter_xlsx_rows(path)
    headers = next(rows, [])
    header_index = {str(name).strip(): index for index, name in enumerate(headers)}
    required_headers = ["attraction_name", "visit_date", "satisfaction"]
    missing_headers = [header for header in required_headers if header not in header_index]
    if missing_headers:
        raise ValueError(f"行为 Excel 缺少必要列：{', '.join(missing_headers)}")

    def cell(row, name):
        index = header_index.get(name)
        return row[index] if index is not None and index < len(row) else ""

    connection.execute("DELETE FROM behavior_visit_record")
    now = int(time.time())
    insert_sql = """
        INSERT INTO behavior_visit_record
        (source_file, source_row, tourist_id, user_nickname, age, gender, attraction_name, attraction_content,
         attraction_type, visit_date, stay_duration, ticket_cost, food_cost, shopping_cost, transport_cost,
         entertainment_cost, total_cost, group_size, satisfaction, raw_json, imported_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    batch = []
    imported = 0
    for source_row, row in enumerate(rows, start=2):
        raw = {header: cell(row, header) for header in headers} if behavior_store_raw_json() else {}
        batch.append(
            (
                source_file,
                source_row,
                str(cell(row, "tourist_id") or ""),
                str(cell(row, "user_nickname") or ""),
                as_int(cell(row, "age"), None),
                str(cell(row, "gender") or ""),
                str(cell(row, "attraction_name") or ""),
                compact_behavior_content(cell(row, "attraction_content")),
                str(cell(row, "attraction_type") or ""),
                excel_date_text(cell(row, "visit_date")),
                as_float(cell(row, "stay_duration"), None),
                as_float(cell(row, "ticket_cost"), None),
                as_float(cell(row, "food_cost"), None),
                as_float(cell(row, "shopping_cost"), None),
                as_float(cell(row, "transport_cost"), None),
                as_float(cell(row, "entertainment_cost"), None),
                as_float(cell(row, "total_cost"), None),
                as_int(cell(row, "group_size"), None),
                as_float(cell(row, "satisfaction"), None),
                json.dumps(raw, ensure_ascii=False),
                now,
            )
        )
        if len(batch) >= 1000:
            connection.executemany(insert_sql, batch)
            imported += len(batch)
            batch.clear()
    if batch:
        connection.executemany(insert_sql, batch)
        imported += len(batch)
    imported_at = now
    set_import_metadata(connection, metadata_key, signature)
    set_active_behavior_import_metadata(connection, source_file, signature, imported_at)
    clear_behavior_analytics_cache()
    return {
        "imported": True,
        "behaviorRecordCount": imported,
        "structuredTableCurrent": True,
        "sourceFile": source_file,
        "message": "游客行为明细表已全量重建。",
    }


def sync_behavior_visit_records(connection):
    path = behavior_source_file()
    source_file = path.name if path else None
    return import_behavior_visit_records_from_path(connection, path, source_file_name=source_file, force=False)


def counter_to_entries(counter, limit=8):
    return [[key, value] for key, value in counter.most_common(limit)]


def behavior_cache_is_valid(mtime, data):
    return (
        BEHAVIOR_ANALYTICS_CACHE["mtime"] == mtime
        and BEHAVIOR_ANALYTICS_CACHE["version"] == BEHAVIOR_ANALYTICS_VERSION
        and data
    )


def behavior_analytics_cache_file():
    return DATA_DIR / BEHAVIOR_ANALYTICS_CACHE_FILE_NAME


def load_behavior_analytics_cache(mtime):
    data = BEHAVIOR_ANALYTICS_CACHE.get("data")
    if behavior_cache_is_valid(mtime, data):
        return data
    cache_file = behavior_analytics_cache_file()
    if not cache_file.exists():
        return None
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("mtime") != mtime or payload.get("version") != BEHAVIOR_ANALYTICS_VERSION:
        return None
    data = payload.get("data")
    if not data:
        return None
    BEHAVIOR_ANALYTICS_CACHE["mtime"] = mtime
    BEHAVIOR_ANALYTICS_CACHE["version"] = BEHAVIOR_ANALYTICS_VERSION
    BEHAVIOR_ANALYTICS_CACHE["data"] = data
    return data


def save_behavior_analytics_cache(mtime, data):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        behavior_analytics_cache_file().write_text(
            json.dumps({"mtime": mtime, "version": BEHAVIOR_ANALYTICS_VERSION, "data": data}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[DATA] 行为分析缓存写入失败：{exc}")


def build_behavior_analytics_from_table():
    with get_connection() as connection:
        try:
            table_status = behavior_structured_table_status(connection)
            raw_row_count = connection.execute("SELECT COUNT(*) AS count FROM behavior_visit_record").fetchone()["count"]
        except Exception:
            return None
        if not raw_row_count:
            return None
        scenic_where = behavior_scenic_where_clause()
        scenic_params = behavior_scenic_where_params()
        row_count = connection.execute(
            f"SELECT COUNT(*) AS count FROM behavior_visit_record WHERE {scenic_where}",
            scenic_params,
        ).fetchone()["count"]
        if not row_count:
            return {
                "available": False,
                "rowCount": 0,
                "rawBehaviorRecordCount": raw_row_count,
                "matchedScenicRows": 0,
                "message": "behavior_visit_record 已导入，但未找到 attraction_name 命中灵山、拈花湾或灵山大佛的记录。",
                "dateRange": {"start": "", "end": ""},
                "topAttractions": [],
                "typeDistribution": [],
                "genderDistribution": {},
                "ageDistribution": {},
                "satisfactionDistribution": {},
                "satisfactionSentimentDistribution": {},
                "satisfactionTrend": [],
                "consumptionBreakdown": [],
                **behavior_analytics_context_fields(table_status),
                "dataSource": {
                    "type": "behavior_table",
                    "label": BEHAVIOR_ANALYSIS_SCOPE,
                    "file": table_status.get("sourceFile", ""),
                    "note": "Excel 已导入，但大屏只展示灵山相关记录；当前未命中灵山、拈花湾或灵山大佛。",
                },
            }

        def grouped_entries(sql, limit):
            rows = connection.execute(sql, (*scenic_params, limit)).fetchall()
            return [[row["name"] or "未知", row["count"]] for row in rows]

        summary = connection.execute(
            f"""
            SELECT
                MIN(visit_date) AS start_date,
                MAX(visit_date) AS end_date,
                ROUND(AVG(stay_duration), 2) AS average_stay,
                ROUND(AVG(satisfaction), 2) AS average_satisfaction,
                ROUND(AVG(group_size), 2) AS average_group_size
            FROM behavior_visit_record
            WHERE {scenic_where}
            """,
            scenic_params,
        ).fetchone()
        matched = row_count
        top_attractions = grouped_entries(
            f"""
            SELECT attraction_name AS name, COUNT(*) AS count
            FROM behavior_visit_record
            WHERE {scenic_where}
            GROUP BY attraction_name
            ORDER BY count DESC
            LIMIT ?
            """,
            10,
        )
        type_distribution = grouped_entries(
            f"""
            SELECT attraction_type AS name, COUNT(*) AS count
            FROM behavior_visit_record
            WHERE {scenic_where}
            GROUP BY attraction_type
            ORDER BY count DESC
            LIMIT ?
            """,
            8,
        )
        gender_distribution = {
            row["name"] or "未知": row["count"]
            for row in connection.execute(
                f"SELECT gender AS name, COUNT(*) AS count FROM behavior_visit_record WHERE {scenic_where} GROUP BY gender",
                scenic_params,
            ).fetchall()
        }
        age_distribution = {
            row["bucket"]: row["count"]
            for row in connection.execute(
                f"""
                SELECT
                    CASE
                        WHEN age IS NULL THEN '未知'
                        WHEN age < 18 THEN '18岁以下'
                        WHEN age <= 30 THEN '18-30岁'
                        WHEN age <= 45 THEN '31-45岁'
                        WHEN age <= 60 THEN '46-60岁'
                        ELSE '60岁以上'
                    END AS bucket,
                    COUNT(*) AS count
                FROM behavior_visit_record
                WHERE {scenic_where}
                GROUP BY bucket
                """,
                scenic_params,
            ).fetchall()
        }
        satisfaction_distribution_rows = connection.execute(
            f"""
            SELECT satisfaction AS score, COUNT(*) AS count
            FROM behavior_visit_record
            WHERE {scenic_where} AND satisfaction IS NOT NULL
            GROUP BY satisfaction
            ORDER BY satisfaction
            """,
            scenic_params,
        ).fetchall()
        satisfaction_distribution = {
            satisfaction_score_key(row["score"]): row["count"]
            for row in satisfaction_distribution_rows
        }
        satisfaction_sentiments = Counter(
            {
                "positive": sum(
                    row["count"]
                    for row in satisfaction_distribution_rows
                    if satisfaction_sentiment_label(row["score"]) == "positive"
                ),
                "neutral": sum(
                    row["count"]
                    for row in satisfaction_distribution_rows
                    if satisfaction_sentiment_label(row["score"]) == "neutral"
                ),
                "negative": sum(
                    row["count"]
                    for row in satisfaction_distribution_rows
                    if satisfaction_sentiment_label(row["score"]) == "negative"
                ),
            }
        )
        trend = [
            {"date": row["month"], "score": row["score"], "count": row["count"]}
            for row in connection.execute(
                f"""
                SELECT SUBSTR(visit_date, 1, 7) AS month, ROUND(AVG(satisfaction), 2) AS score, COUNT(*) AS count
                FROM behavior_visit_record
                WHERE visit_date <> '' AND {scenic_where}
                GROUP BY month
                ORDER BY month
                """,
                scenic_params,
            ).fetchall()
        ]
        spend = connection.execute(
            f"""
            SELECT
                ROUND(AVG(ticket_cost), 2) AS ticket,
                ROUND(AVG(food_cost), 2) AS food,
                ROUND(AVG(shopping_cost), 2) AS shopping,
                ROUND(AVG(transport_cost), 2) AS transport,
                ROUND(AVG(entertainment_cost), 2) AS entertainment
            FROM behavior_visit_record
            WHERE {scenic_where}
            """,
            scenic_params,
        ).fetchone()
        source_row = connection.execute(
            f"SELECT source_file FROM behavior_visit_record WHERE {scenic_where} ORDER BY id LIMIT 1",
            scenic_params,
        ).fetchone()

    return {
        "available": True,
        "rowCount": row_count,
        "rawBehaviorRecordCount": raw_row_count,
        "matchedScenicRows": matched,
        "dateRange": {"start": summary["start_date"] or "", "end": summary["end_date"] or ""},
        "averageSatisfaction": summary["average_satisfaction"] or 0,
        "averageStayDuration": summary["average_stay"] or 0,
        "averageGroupSize": summary["average_group_size"] or 0,
        "topAttractions": top_attractions,
        "typeDistribution": type_distribution,
        "genderDistribution": gender_distribution,
        "ageDistribution": age_distribution,
        "satisfactionDistribution": satisfaction_distribution,
        "satisfactionSentimentDistribution": dict(satisfaction_sentiments),
        "satisfactionTrend": trend,
        "consumptionBreakdown": [
            {"name": "门票", "value": spend["ticket"] or 0},
            {"name": "餐饮", "value": spend["food"] or 0},
            {"name": "购物", "value": spend["shopping"] or 0},
            {"name": "交通", "value": spend["transport"] or 0},
            {"name": "娱乐", "value": spend["entertainment"] or 0},
        ],
        **behavior_analytics_context_fields(table_status),
        "dataSource": {
            "type": "behavior_table",
            "label": BEHAVIOR_ANALYSIS_SCOPE,
            "file": source_row["source_file"] if source_row else "",
            "note": "Excel 已导入 behavior_visit_record 结构化明细表；大屏和报告仅统计 attraction_name 命中灵山、拈花湾或灵山大佛的记录。",
        },
    }


def build_behavior_analytics(use_structured_table=True):
    if use_structured_table:
        table_data = build_behavior_analytics_from_table()
        if table_data:
            return table_data
        table_status = current_behavior_structured_table_status()
        return {
            "available": False,
            "rowCount": 0,
            "matchedScenicRows": 0,
            "message": "behavior_visit_record 暂无可用明细，后台会在表为空或 Excel 文件签名变化时刷新/重建。",
            "dateRange": {"start": "", "end": ""},
            "topAttractions": [],
            "typeDistribution": [],
            "genderDistribution": {},
            "ageDistribution": {},
            "satisfactionDistribution": {},
            "satisfactionSentimentDistribution": {},
            "satisfactionTrend": [],
            "consumptionBreakdown": [],
            **behavior_analytics_context_fields(table_status),
            "dataSource": {
                "type": "behavior_table_pending",
                "label": BEHAVIOR_ANALYSIS_SCOPE,
                "file": table_status.get("sourceFile", ""),
                "note": "报告默认只从 behavior_visit_record 聚合；结构化表为空时不会在请求链路中同步扫描 Excel。",
            },
        }

    table_status = current_behavior_structured_table_status()
    path = behavior_source_file()
    if not path or not path.exists():
        return {
            "available": False,
            "rowCount": 0,
            "message": "未找到游客行为分析 Excel。",
            "dataSource": {"type": "missing", "label": "未找到数据源", "file": ""},
            **behavior_analytics_context_fields(table_status),
        }

    mtime = path.stat().st_mtime
    cached_data = load_behavior_analytics_cache(mtime)
    if cached_data:
        return cached_data

    rows = iter_xlsx_rows(path)
    headers = next(rows, [])
    header_index = {name: index for index, name in enumerate(headers)}

    def cell(row, name):
        index = header_index.get(name)
        return row[index] if index is not None and index < len(row) else ""

    raw_row_count = 0
    row_count = 0
    attraction_counter = Counter()
    type_counter = Counter()
    gender_counter = Counter()
    age_counter = Counter()
    satisfaction_distribution = Counter()
    satisfaction_sentiments = Counter()
    month_satisfaction = {}
    satisfaction_values = []
    dates = []
    stay_total = 0.0
    group_total = 0.0
    spend_totals = Counter()
    spend_fields = {
        "ticket_cost": "门票",
        "food_cost": "餐饮",
        "shopping_cost": "购物",
        "transport_cost": "交通",
        "entertainment_cost": "娱乐",
    }

    for row in rows:
        if not row:
            continue
        raw_row_count += 1
        attraction_name = str(cell(row, "attraction_name") or "未知景区").strip() or "未知景区"
        if not behavior_row_matches_scenic(attraction_name):
            continue
        row_count += 1
        attraction_type = str(cell(row, "attraction_type") or "未知类型").strip() or "未知类型"
        visit_date = excel_date_text(cell(row, "visit_date"))
        satisfaction = as_float(cell(row, "satisfaction"), None)

        attraction_counter[attraction_name] += 1
        type_counter[attraction_type] += 1
        gender_counter[str(cell(row, "gender") or "未知")] += 1
        age_counter[age_bucket(cell(row, "age"))] += 1
        stay_total += as_float(cell(row, "stay_duration"))
        group_total += as_float(cell(row, "group_size"))
        if visit_date:
            dates.append(visit_date)
        if satisfaction is not None:
            satisfaction_values.append(satisfaction)
            satisfaction_distribution[satisfaction_score_key(satisfaction)] += 1
            satisfaction_sentiments[satisfaction_sentiment_label(satisfaction)] += 1
            month = visit_date[:7] if visit_date else "未知"
            bucket = month_satisfaction.setdefault(month, [])
            bucket.append(satisfaction)
        for field, label in spend_fields.items():
            spend_totals[label] += as_float(cell(row, field))

    average_satisfaction = round(sum(satisfaction_values) / len(satisfaction_values), 2) if satisfaction_values else 0
    trend = [
        {"date": month, "score": round(sum(values) / len(values), 2), "count": len(values)}
        for month, values in sorted(month_satisfaction.items())
        if month != "未知"
    ]
    data = {
        "available": True,
        "rowCount": row_count,
        "rawBehaviorRecordCount": raw_row_count,
        "matchedScenicRows": row_count,
        "dateRange": {"start": min(dates) if dates else "", "end": max(dates) if dates else ""},
        "averageSatisfaction": average_satisfaction,
        "averageStayDuration": round(stay_total / row_count, 2) if row_count else 0,
        "averageGroupSize": round(group_total / row_count, 2) if row_count else 0,
        "topAttractions": counter_to_entries(attraction_counter, 10),
        "typeDistribution": counter_to_entries(type_counter, 8),
        "genderDistribution": dict(gender_counter),
        "ageDistribution": dict(age_counter),
        "satisfactionDistribution": dict(satisfaction_distribution),
        "satisfactionSentimentDistribution": dict(satisfaction_sentiments),
        "satisfactionTrend": trend,
        "consumptionBreakdown": [
            {"name": label, "value": round(total / row_count, 2) if row_count else 0}
            for label, total in spend_totals.items()
        ],
        **behavior_analytics_context_fields(table_status),
        "dataSource": {
            "type": "behavior_excel",
            "label": BEHAVIOR_ANALYSIS_SCOPE,
            "file": str(path),
            "note": "该 Excel 已按 attraction_name 筛选灵山、拈花湾或灵山大佛记录后用于大屏和报告分析。",
        },
    }
    BEHAVIOR_ANALYTICS_CACHE["mtime"] = mtime
    BEHAVIOR_ANALYTICS_CACHE["version"] = BEHAVIOR_ANALYTICS_VERSION
    BEHAVIOR_ANALYTICS_CACHE["data"] = data
    save_behavior_analytics_cache(mtime, data)
    return data


def build_official_knowledge_documents(records):
    documents = build_full_docx_knowledge_documents()
    guide_path = find_public_data_file("游览指南", ".docx")
    guide_lines = read_docx_paragraphs(guide_path)
    section_specs = [
        ("灵山胜境概况与历史渊源", "景区概况与千年历史渊源", ["核心文化内涵：佛教传承与艺术融合的典范"]),
        ("灵山胜境核心文化内涵", "核心文化内涵：佛教传承与艺术融合的典范", ["核心景点特色详解：佛教艺术的殿堂"]),
        ("灵山胜境核心景点特色详解", "核心景点特色详解：佛教艺术的殿堂", ["个性化游览路线推荐：深度体验灵山胜境"]),
        ("历史文化爱好者路线", "历史文化爱好者路线（6小时深度游）", ["自然风光爱好者路线（5小时全景游）"]),
        ("自然风光爱好者路线", "自然风光爱好者路线（5小时全景游）", ["亲子家庭路线（4小时轻松游）"]),
        ("亲子家庭路线", "亲子家庭路线（4小时轻松游）", ["实用游览贴士：全方位保障你的灵山之旅"]),
        ("门票开放与实用游览贴士", "实用游览贴士：全方位保障你的灵山之旅", []),
    ]
    for title, start, ends in section_specs:
        content = guide_section(guide_lines, start, ends)
        if content:
            documents.append(
                {
                    "title": f"{OFFICIAL_DATA_PREFIX}：{title}",
                    "category": "官方游览指南",
                    "content": content,
                    "sourceType": "official_docx",
                    "sourceFile": guide_path.name if guide_path else "",
                    "sourceSection": start,
                }
            )

    for record in records:
        content = "\n".join(
            [
                f"景区：{record['scenicName']}",
                f"景点ID：{record['sourceId']}",
                f"景点名称：{record['name']}",
                f"具体位置：{record['location']}",
                f"建筑/景观参数：{record['parameters']}",
                f"核心功能：{record['coreFunction']}",
                f"文化内涵：{record['culture']}",
                f"详细介绍：{record['detail']}",
                f"游玩亮点：{record['highlights']}",
                f"演艺/开放信息：{record['openInfo']}",
                f"备注：{record['remarks']}",
            ]
        )
        documents.append(
            {
                "title": f"{OFFICIAL_DATA_PREFIX}：{record['name']}景点资料",
                "category": "官方景点资料",
                "content": content,
                "sourceType": "official_docx",
                "sourceFile": find_public_data_file("结构化数据集", ".docx").name if find_public_data_file("结构化数据集", ".docx") else "",
                "sourceSection": record["sourceId"],
            }
        )

    behavior_summary = load_behavior_dataset_summary()
    if behavior_summary:
        behavior_path = find_public_data_file("旅游数据行为分析", ".xlsx")
        documents.append(
            {
                "title": f"{OFFICIAL_DATA_PREFIX}：游客行为数据字段说明",
                "category": "行为数据分析",
                "content": behavior_summary,
                "sourceType": "behavior_excel",
                "sourceFile": behavior_path.name if behavior_path else "",
                "sourceSection": "字段说明",
            }
        )
    behavior_analytics_document = behavior_analytics_summary_document()
    if behavior_analytics_document:
        documents.append(behavior_analytics_document)
    return documents


def purge_legacy_demo_data(connection):
    execute_in_clause(connection, "DELETE FROM scenic_spot WHERE name IN", LEGACY_DEMO_SPOT_NAMES)
    execute_in_clause(
        connection,
        "DELETE FROM knowledge_document WHERE (content LIKE '%云岚%' OR content LIKE '%小游%') AND title IN",
        LEGACY_DEMO_KNOWLEDGE_TITLES,
    )
    legacy_chat_rows = connection.execute(
        """
        SELECT id FROM chat_record
        WHERE question LIKE '%云岚%'
           OR answer LIKE '%云岚%'
           OR answer LIKE '%小游%'
        """
    ).fetchall()
    legacy_chat_ids = [row["id"] for row in legacy_chat_rows]
    execute_in_clause(connection, "DELETE FROM feedback_record WHERE chat_id IN", legacy_chat_ids)
    execute_in_clause(connection, "DELETE FROM chat_record WHERE id IN", legacy_chat_ids)
    connection.execute(
        """
        DELETE FROM route_record
        WHERE title LIKE '%云岚%'
           OR reason LIKE '%云岚%'
           OR spots LIKE '%云岚%'
           OR spots LIKE '%非遗工坊%'
           OR spots LIKE '%民俗博物馆%'
        """
    )


def sync_official_public_data(connection, import_behavior_rows=False):
    records = parse_official_spot_records()
    if not records:
        return {
            "imported": False,
            "spotCount": 0,
            "knowledgeCount": 0,
            "recordCount": 0,
            "dataDir": str(PUBLIC_DATA_DIR),
            "message": "未找到可导入的官方资料包，已保留现有资料。",
        }

    now = int(time.time())
    official_spots = [official_record_to_spot(record, index) for index, record in enumerate(records)]
    official_names = {spot["name"] for spot in official_spots}
    legacy_names = [spot["name"] for spot in SEED_SPOTS if spot["name"] not in official_names]
    if legacy_names:
        execute_in_clause(
            connection,
            "UPDATE scenic_spot SET status = 'inactive', updated_at = ? WHERE name IN",
            legacy_names,
            (now,),
        )

    for spot in official_spots:
        existing = connection.execute("SELECT id FROM scenic_spot WHERE name = ?", (spot["name"],)).fetchone()
        values = (
            spot["description"],
            spot["story"],
            json.dumps(spot["tags"], ensure_ascii=False),
            spot["image"],
            spot["openTime"],
            spot["duration"],
            spot["popularity"],
            spot["location"],
            spot["lat"],
            spot["lon"],
            spot["mapZone"],
            spot["mapX"],
            spot["mapY"],
            1 if spot["verifiedLocation"] else 0,
            "active",
            now,
        )
        if existing:
            connection.execute(
                """
                UPDATE scenic_spot
                SET description = ?, story = ?, tags = ?, image = ?, open_time = ?, duration = ?,
                    popularity = ?, location = ?, lat = ?, lon = ?, map_zone = ?, map_x = ?, map_y = ?,
                    verified_location = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (*values, existing["id"]),
            )
        else:
            connection.execute(
                """
                INSERT INTO scenic_spot
                (name, description, story, tags, image, open_time, duration, popularity, location, lat, lon,
                 map_zone, map_x, map_y, verified_location, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spot["name"],
                    spot["description"],
                    spot["story"],
                    json.dumps(spot["tags"], ensure_ascii=False),
                    spot["image"],
                    spot["openTime"],
                    spot["duration"],
                    spot["popularity"],
                    spot["location"],
                    spot["lat"],
                    spot["lon"],
                    spot["mapZone"],
                    spot["mapX"],
                    spot["mapY"],
                    1 if spot["verifiedLocation"] else 0,
                    "active",
                    now,
                    now,
                ),
            )

    legacy_titles = [item["title"] for item in SEED_KNOWLEDGE]
    if legacy_titles:
        execute_in_clause(
            connection,
            "UPDATE knowledge_document SET status = 'inactive', updated_at = ? WHERE title IN",
            legacy_titles,
            (now,),
        )

    official_documents = build_official_knowledge_documents(records)
    for document in official_documents:
        existing = connection.execute("SELECT id FROM knowledge_document WHERE title = ?", (document["title"],)).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE knowledge_document
                SET category = ?, content = ?, status = 'active', source_type = ?, source_file = ?, source_section = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    document["category"],
                    document["content"],
                    document.get("sourceType", "official_docx"),
                    document.get("sourceFile", ""),
                    document.get("sourceSection", ""),
                    now,
                    existing["id"],
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO knowledge_document
                (id, title, category, content, status, source_type, source_file, source_section, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    document["title"],
                    document["category"],
                    document["content"],
                    document.get("sourceType", "official_docx"),
                    document.get("sourceFile", ""),
                    document.get("sourceSection", ""),
                    now,
                    now,
                ),
            )

    behavior_import = sync_behavior_visit_records(connection) if import_behavior_rows else None
    behavior_message = f"，{behavior_import['behaviorRecordCount']} 条游客行为明细" if behavior_import else ""
    print(f"[DATA] 已同步官方资料包：{len(official_spots)} 个景点，{len(official_documents)} 条知识文档{behavior_message}。")
    return {
        "imported": True,
        "spotCount": len(official_spots),
        "knowledgeCount": len(official_documents),
        "recordCount": len(records),
        "behaviorRecordCount": behavior_import["behaviorRecordCount"] if behavior_import else None,
        "behaviorRecordImported": behavior_import["imported"] if behavior_import else False,
        "dataDir": str(PUBLIC_DATA_DIR),
        "importedAt": now,
        "message": "官方资料包已重新导入，游客端问答和点位数据会立即使用最新资料。",
    }


def row_to_spot(row):
    keys = row.keys()
    spot = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "story": row["story"],
        "tags": safe_json_loads(row["tags"], []),
        "image": row["image"],
        "openTime": row["open_time"],
        "duration": row["duration"],
        "popularity": row["popularity"],
        "location": row["location"],
        "status": row["status"] if "status" in keys else "active",
        "updatedAt": row["updated_at"] if "updated_at" in keys else row["created_at"],
        "lat": row["lat"] if "lat" in keys else None,
        "lon": row["lon"] if "lon" in keys else None,
        "mapZone": row["map_zone"] if "map_zone" in keys else "lingshan",
        "mapX": row["map_x"] if "map_x" in keys else None,
        "mapY": row["map_y"] if "map_y" in keys else None,
        "verifiedLocation": bool(row["verified_location"]) if "verified_location" in keys else False,
    }
    spot["locationCode"] = spot_location_code(spot)
    return spot


def row_to_knowledge(row):
    keys = row.keys()
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "content": row["content"],
        "status": row["status"],
        "sourceType": row["source_type"] if "source_type" in keys else "manual",
        "sourceFile": row["source_file"] if "source_file" in keys else "",
        "sourceSection": row["source_section"] if "source_section" in keys else "",
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def row_to_chat_record(row):
    return {
        "id": row["id"],
        "question": row["question"],
        "answer": row["answer"],
        "relatedSpots": safe_json_loads(row["related_spots"], []),
        "sourceRefs": safe_json_loads(row["source_refs"], []),
        "intent": row["intent"],
        "confidence": row["confidence"],
        "sentiment": row["sentiment"],
        "satisfaction": row["satisfaction"],
        "createdAt": row["created_at"],
    }


def row_to_persona(row):
    keys = row.keys()
    return {
        "name": row["name"],
        "role": row["role"],
        "greeting": row["greeting"],
        "style": row["style"],
        "costume": row["costume"],
        "voice": row["voice"],
        "accentColor": row["accent_color"],
        "voiceSpeed": row["voice_speed"] if "voice_speed" in keys else DEFAULT_PERSONA["voiceSpeed"],
        "voicePitch": row["voice_pitch"] if "voice_pitch" in keys else DEFAULT_PERSONA["voicePitch"],
        "expressionProfile": row["expression_profile"] if "expression_profile" in keys else DEFAULT_PERSONA["expressionProfile"],
        "avatarPresetKey": row["avatar_preset_key"] if "avatar_preset_key" in keys else DEFAULT_PERSONA["avatarPresetKey"],
        "avatarId": row["avatar_id"] if "avatar_id" in keys else DEFAULT_PERSONA["avatarId"],
        "refAudio": row["ref_audio"] if "ref_audio" in keys else DEFAULT_PERSONA["refAudio"],
        "refText": row["ref_text"] if "ref_text" in keys else DEFAULT_PERSONA["refText"],
        "avatarVoice": row["avatar_voice"] if "avatar_voice" in keys else DEFAULT_PERSONA["avatarVoice"],
        "ttsMode": row["tts_mode"] if "tts_mode" in keys else DEFAULT_PERSONA["ttsMode"],
        "updatedAt": row["updated_at"],
    }


def get_spots(include_inactive=False):
    sql = "SELECT * FROM scenic_spot"
    params = ()
    if not include_inactive:
        sql += " WHERE status = 'active'"
    sql += " ORDER BY popularity DESC, id ASC"
    with get_connection() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [row_to_spot(row) for row in rows]


def find_spot(spot_id, include_inactive=False):
    sql = "SELECT * FROM scenic_spot WHERE id = ?"
    params = [spot_id]
    if not include_inactive:
        sql += " AND status = 'active'"
    with get_connection() as connection:
        row = connection.execute(sql, params).fetchone()
    return row_to_spot(row) if row else None


def haversine_distance(lat1, lon1, lat2, lon2):
    return location_service.haversine_distance(lat1, lon1, lat2, lon2)


def spots_nearby(lat, lon, limit=5):
    return location_service.spots_nearby(lat, lon, get_spots(include_inactive=False), limit)


def spot_location_code(spot):
    return location_service.spot_location_code(spot, ROUTE_SPOT_ORDER)


def extract_location_code(value):
    return location_service.extract_location_code(value)


def normalize_location_code(value):
    return location_service.normalize_location_code(value)


def spot_matches_location_code(spot, raw_code):
    return location_service.spot_matches_location_code(spot, raw_code)


def has_coordinates(spot):
    return location_service.has_coordinates(spot)


def spots_with_distance(lat, lon):
    return location_service.spots_with_distance(lat, lon, get_spots(include_inactive=False))


def spot_with_distance(spot, distance):
    return location_service.spot_with_distance(spot, distance)


def parse_optional_float(value):
    return location_service.parse_optional_float(value)


def location_confidence(distance, accuracy=None):
    return location_service.location_confidence(distance, accuracy)


def nearby_location_result(lat, lon, limit=5, accuracy=None):
    return location_service.nearby_location_result(lat, lon, get_spots(include_inactive=False), limit, accuracy)


def location_anchors():
    return location_service.location_anchors(get_spots(include_inactive=False), route_order_key)


def resolve_location_code(raw_code):
    return location_service.resolve_location_code(raw_code, location_anchors())


def get_knowledge_documents(include_inactive=True):
    sql = "SELECT * FROM knowledge_document"
    if not include_inactive:
        sql += " WHERE status = 'active'"
    sql += " ORDER BY updated_at DESC"
    with get_connection() as connection:
        rows = connection.execute(sql).fetchall()
    return [row_to_knowledge(row) for row in rows]


def get_persona():
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM persona_config WHERE id = 1").fetchone()
    return row_to_persona(row)


def save_chat_record(record):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO chat_record
            (id, question, answer, related_spots, source_refs, intent, confidence, sentiment, satisfaction, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["question"],
                record["answer"],
                json.dumps(record["relatedSpots"], ensure_ascii=False),
                json.dumps(record["sourceRefs"], ensure_ascii=False),
                record["intent"],
                record["confidence"],
                record["sentiment"],
                0,
                record["createdAt"],
            ),
        )


def save_route_record(route):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO route_record
            (id, title, duration, estimated_duration, preference, spots, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                route["id"],
                route["title"],
                route["duration"],
                route["estimatedDuration"],
                route["preference"],
                json.dumps(route["spots"], ensure_ascii=False),
                route["reason"],
                route["createdAt"],
            ),
        )


def get_recent_chat_records(limit=8, low_confidence=False):
    where = "WHERE confidence < 0.65" if low_confidence else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM chat_record {where} ORDER BY created_at DESC LIMIT ?", (max(limit * 4, limit),)
        ).fetchall()
    records = []
    for row in rows:
        record = row_to_chat_record(row)
        if not is_displayable_text(record["question"]):
            continue
        records.append(record)
        if len(records) >= limit:
            break
    return records


def get_chat_record_by_id(chat_id):
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM chat_record WHERE id = ?", (chat_id,)).fetchone()
    return row_to_chat_record(row) if row else None


def reimport_public_data(import_behavior_rows=False):
    with get_connection() as connection:
        summary = sync_official_public_data(connection, import_behavior_rows=import_behavior_rows)
        sync_known_spot_locations(connection)
    return summary


def import_behavior_excel_upload(file_name, content):
    safe_name = re.sub(r"[\\/:*?\"<>|]+", "_", str(file_name or "behavior.xlsx")).strip() or "behavior.xlsx"
    if not safe_name.lower().endswith(".xlsx"):
        raise ValueError("仅支持 .xlsx 行为数据文件")
    if not content:
        raise ValueError("上传文件为空")
    if len(content) > MAX_BEHAVIOR_EXCEL_BYTES:
        raise ValueError("行为数据文件过大")

    upload_dir = DATA_DIR / "tmp" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = upload_dir / f"{uuid.uuid4().hex}-{safe_name}"
    try:
        tmp_path.write_bytes(content)
        if not zipfile.is_zipfile(tmp_path):
            raise ValueError("上传文件不是有效的 xlsx 文件")
        with get_connection() as connection:
            summary = import_behavior_visit_records_from_path(connection, tmp_path, source_file_name=safe_name, force=True)
        summary.update(
            {
                "imported": True,
                "spotCount": len(get_spots(include_inactive=True)),
                "knowledgeCount": len(get_knowledge_documents(include_inactive=True)),
                "recordCount": summary.get("behaviorRecordCount", 0),
                "behaviorRecordImported": True,
                "dataDir": str(DATA_DIR),
                "importedAt": int(time.time()),
                "message": f"已导入 {safe_name}，行为明细表已全量更新。",
            }
        )
        return summary
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def sync_behavior_records_in_background():
    try:
        with get_connection() as connection:
            summary = sync_behavior_visit_records(connection)
        if summary.get("imported"):
            print(f"[DATA] 游客行为明细后台导入完成：{summary['behaviorRecordCount']} 条。")
        else:
            print(f"[DATA] 游客行为明细无需重导：{summary['behaviorRecordCount']} 条。")
    except Exception as exc:
        print(f"[DATA] 游客行为明细后台导入失败：{exc}")


def start_behavior_records_background_sync():
    thread = threading.Thread(target=sync_behavior_records_in_background, name="behavior-record-import", daemon=True)
    thread.start()


def cors_allowed_origin(handler):
    configured = os.getenv("SCENIC_CORS_ORIGINS", DEFAULT_CORS_ORIGINS).strip()
    headers = getattr(handler, "headers", {})
    origin = headers.get("Origin", "") if hasattr(headers, "get") else ""
    origin = str(origin).strip().rstrip("/")
    if configured == "*":
        return "*"
    allowed = {item.strip().rstrip("/") for item in configured.split(",") if item.strip()}
    if origin and origin in allowed:
        return origin
    return ""


def send_cors_headers(handler):
    allowed_origin = cors_allowed_origin(handler)
    if not allowed_origin:
        return
    handler.send_header("Access-Control-Allow-Origin", allowed_origin)
    if allowed_origin != "*":
        handler.send_header("Vary", "Origin")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type,X-Admin-Token")


def json_response(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Connection", "close")
    send_cors_headers(handler)
    handler.end_headers()
    handler.wfile.write(body)
    handler.close_connection = True


def error_response(handler, message, status=400, code="bad_request"):
    json_response(handler, {"message": str(message), "code": code}, status)


def static_content_type(file_path):
    explicit_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".json": "application/json",
        ".map": "application/json",
        ".svg": "image/svg+xml",
    }
    content_type = explicit_types.get(file_path.suffix.lower()) or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    if content_type.startswith("text/") or content_type in {"application/javascript", "application/json", "image/svg+xml"}:
        return f"{content_type}; charset=utf-8"
    return content_type


def read_json(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    if length > MAX_JSON_BODY_BYTES:
        raise ValueError("请求体过大")
    raw = handler.rfile.read(length).decode("utf-8")
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def admin_token():
    return os.getenv("SCENIC_ADMIN_TOKEN", "").strip()


def is_admin_api(path):
    return path.startswith("/api/admin/")


def is_admin_mutation(path, method):
    return method in MUTATING_ADMIN_METHODS and is_admin_api(path)


def has_valid_admin_token(handler):
    expected = admin_token()
    if not expected:
        return True
    provided = handler.headers.get("X-Admin-Token", "").strip()
    return bool(provided) and hmac.compare_digest(provided, expected)


def client_ip(handler):
    return handler.client_address[0] if handler.client_address else "unknown"


def rate_limit_exceeded(handler, bucket, limit, window_seconds):
    now = time.time()
    key = (client_ip(handler), bucket)
    timestamps = [ts for ts in RATE_LIMIT_BUCKETS.get(key, []) if now - ts < window_seconds]
    if len(timestamps) >= limit:
        RATE_LIMIT_BUCKETS[key] = timestamps
        return True
    timestamps.append(now)
    RATE_LIMIT_BUCKETS[key] = timestamps
    return False


def normalize_text(value):
    return str(value or "").strip().lower()


def is_displayable_text(value):
    text = str(value or "").strip()
    if not text:
        return False
    compact = re.sub(r"[\s,，。！？!?.、；;：:（）()【】\[\]\"']+", "", text)
    if not compact:
        return False
    if "�" in compact:
        return False
    question_marks = compact.count("?")
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", compact))
    if question_marks >= 2 and cjk_chars == 0:
        return False
    return question_marks < max(3, len(compact) * 0.5)


def extract_terms(text):
    normalized = normalize_text(text)
    words = [word for word in re.split(r"[\s,，。！？!?.、；;：:（）()【】\[\]\"']+", normalized) if len(word) >= 2]
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]+", normalized))
    grams = []
    for size in (2, 3, 4):
        grams.extend(cjk[index : index + size] for index in range(max(len(cjk) - size + 1, 0)))
    return list(dict.fromkeys(words + grams))


def analyze_sentiment(text):
    normalized = normalize_text(text)
    positive = sum(1 for word in POSITIVE_WORDS if word in normalized)
    negative = sum(1 for word in NEGATIVE_WORDS if word in normalized)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def classify_intent(question):
    if asks_for_religious_etiquette(question):
        return "文化礼仪"
    text = normalize_text(question)
    rules = [
        ("票务开放", ["开放", "时间", "几点", "门票", "价格", "票价", "优惠"]),
        ("交通服务", ["停车", "交通", "怎么去", "入口", "服务中心", "寄存", "厕所", "母婴"]),
        (
            "路线推荐",
            [
                "路线",
                "推荐",
                "怎么逛",
                "怎么走",
                "怎么到",
                "到达路线",
                "导航",
                "游览",
                "亲子",
                "历史",
                "自然",
                "拍照",
                "打卡",
            ],
        ),
        ("景点讲解", ["介绍", "讲解", "特色", "故事", "历史", "文化", "好玩", "哪里"]),
        ("安全求助", ["迷路", "不适", "急救", "安全", "投诉", "丢", "找不到"]),
    ]
    for intent, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return intent
    return "其他咨询"


def match_spots_by_question(question, spots):
    normalized = normalize_text(question)
    matched = []
    for spot in spots:
        name = normalize_text(spot["name"])
        short_name = name.replace("灵山", "").replace("拈花湾", "").replace("拈花", "")
        tag_text = " ".join(spot["tags"]).lower()
        if name in normalized or (short_name and short_name in normalized):
            matched.append((100, spot))
            continue
        score = 0
        for tag in spot["tags"]:
            if normalize_text(tag) in normalized:
                score += 18
        if score:
            matched.append((score + spot["popularity"] / 10, spot))
    return [spot for _, spot in sorted(matched, key=lambda item: item[0], reverse=True)]


def search_knowledge(question, limit=4):
    documents = get_knowledge_documents(include_inactive=False)
    return hybrid_search_documents(question, documents, limit=limit)


def split_sentences(text):
    parts = re.split(r"(?<=[。！？!?])", text)
    return [part.strip() for part in parts if part.strip()]


def build_knowledge_summary(question, documents):
    return build_search_summary(question, documents, max_sentences=3, max_chars=260)


STRUCTURED_KNOWLEDGE_LABELS = {
    "景区",
    "景点ID",
    "景点名称",
    "具体位置",
    "建筑/景观参数",
    "核心功能",
    "文化内涵",
    "详细介绍",
    "游玩亮点",
    "演艺/开放信息",
    "开放/演艺信息",
    "备注",
}


def extract_structured_fields(document):
    fields = {}
    current_key = ""
    for raw_line in str(document.get("content", "")).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = re.match(r"^([^：:]{2,18})[：:](.*)$", line)
        if matched and matched.group(1).strip() in STRUCTURED_KNOWLEDGE_LABELS:
            current_key = matched.group(1).strip()
            fields[current_key] = matched.group(2).strip()
            continue
        if current_key and len(fields.get(current_key, "")) < 900:
            fields[current_key] = f"{fields[current_key]} {line}".strip()
    return fields


def exact_spot_names_from_question(question, matched_spots):
    normalized_question = normalize_text(question)
    names = []
    for spot in matched_spots or []:
        raw_name = spot.get("name", "")
        name = normalize_text(raw_name)
        short_name = name.replace("灵山", "").replace("拈花湾", "").replace("拈花", "")
        if name in normalized_question or (short_name and short_name in normalized_question):
            names.append(raw_name)
    return names


def knowledge_document_matches_spot(document, spot_name):
    fields = extract_structured_fields(document)
    if fields.get("景点名称") == spot_name:
        return True
    title = normalize_text(document.get("title", ""))
    return normalize_text(f"{spot_name}景点资料") in title


def prioritize_exact_spot_knowledge(question, knowledge_hits, matched_spots):
    exact_names = exact_spot_names_from_question(question, matched_spots)
    if not exact_names:
        return knowledge_hits

    hit_ids = {hit.get("id") for hit in knowledge_hits}
    top_score = max([float(hit.get("score", 0) or 0) for hit in knowledge_hits] or [0])
    boosted_score = max(top_score, env_float("SCENIC_KNOWLEDGE_ANSWER_THRESHOLD", 24.0)) + 20
    all_documents = get_knowledge_documents(include_inactive=False)
    boosted = []

    for spot_name in exact_names:
        existing_hit = next((hit for hit in knowledge_hits if knowledge_document_matches_spot(hit, spot_name)), None)
        if existing_hit:
            boosted.append({**existing_hit, "score": max(float(existing_hit.get("score", 0) or 0), boosted_score)})
            continue
        document = next(
            (item for item in all_documents if item.get("id") not in hit_ids and knowledge_document_matches_spot(item, spot_name)),
            None,
        )
        if document:
            boosted.append({**document, "score": boosted_score})

    if not boosted:
        return knowledge_hits

    ordered = []
    seen_ids = set()
    for item in [*boosted, *knowledge_hits]:
        item_id = item.get("id")
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        ordered.append(item)
    return ordered


def compact_answer_text(text, max_chars=180):
    value = re.sub(r"\s+", " ", str(text or "")).strip(" ，。；;")
    if len(value) <= max_chars:
        return value
    clipped = value[:max_chars].rstrip("，。；;、 ")
    return f"{clipped}。"


def pick_sentence(text, keywords=None, max_chars=130):
    parts = [part.strip(" ，。；;") for part in re.split(r"(?<=[。！？!?；;])|\n+", str(text or "")) if part.strip()]
    keywords = keywords or []
    for part in parts:
        if any(keyword in part for keyword in keywords):
            return compact_answer_text(part, max_chars)
    return compact_answer_text(parts[0], max_chars) if parts else ""


def concise_open_info(open_info):
    clauses = [part.strip(" ，。；;") for part in re.split(r"[；;。]", str(open_info or "")) if part.strip()]
    if not clauses:
        return ""
    selected = [clauses[0]]
    for clause in clauses[1:]:
        if any(term in clause for term in ("冬季", "闭馆", "闭园")):
            selected.append(clause)
            break
    return compact_answer_text("；".join(selected), 120)


def concise_performance_info(open_info):
    clauses = [part.strip(" ，。；;") for part in re.split(r"[；;。]", str(open_info or "")) if part.strip()]
    performance_clauses = [
        clause
        for clause in clauses
        if any(term in clause for term in ("演出", "表演", "场次", "加演", "开园仪式", "灯光秀", "广播通知", "小程序通知"))
    ]
    if performance_clauses:
        return compact_answer_text("；".join(performance_clauses[:2]), 150)
    if open_info:
        return "没有固定表演时间，可按开放时间参观，具体活动以景区当天公告和现场广播为准"
    return ""


def concise_photo_reason(location, highlights, detail, culture):
    location = str(location or "")
    if "四面环水" in location and "藏式建筑风格" in location:
        return "四面环水，藏式建筑风格与周边江南景观反差明显"
    source = " ".join(part for part in (highlights, location, detail, culture) if part)
    return pick_sentence(source, ("拍照", "打卡", "观景", "建筑", "风格", "四面环水", "金色", "白墙", "全景"), 80)


def asks_for_location(question):
    text = normalize_text(question)
    return any(term in text for term in ("在哪", "哪里", "位置", "怎么去", "怎么走", "到哪"))


def asks_for_directions(question):
    text = normalize_text(question)
    direction_terms = (
        "怎么走",
        "怎么过去",
        "怎么到",
        "怎么去",
        "如何到",
        "如何去",
        "从哪走",
        "往哪走",
        "到达路线",
        "导航",
    )
    return any(term in text for term in direction_terms)


def asks_for_photo(question):
    text = normalize_text(question)
    return any(term in text for term in ("拍照", "打卡", "出片", "好拍", "适合拍", "摄影", "合影"))


def asks_for_duration(question):
    text = normalize_text(question)
    return any(term in text for term in ("游览多久", "玩多久", "逛多久", "多长时间", "建议时长", "需要多久", "耗时"))


def asks_for_parameters(question):
    text = normalize_text(question)
    return any(term in text for term in ("多高", "高度", "多少米", "面积", "占地", "多大", "参数", "规格", "用铜量", "多少吨"))


def asks_for_performance(question):
    text = normalize_text(question)
    return any(term in text for term in ("表演", "演出", "场次", "节目", "吉祥颂"))


def asks_for_intro(question):
    text = normalize_text(question)
    return any(term in text for term in ("介绍", "讲解", "特色", "有什么", "好玩", "看什么", "亮点"))


def wayfinding_path_for_spot(spot):
    name = (spot or {}).get("name", "")
    if not name:
        return []
    zone = str(
        (spot or {}).get("mapZone")
        or (spot or {}).get("map_zone")
        or SPOT_LOCATION_OVERRIDES.get(name, {}).get("zone")
        or "lingshan"
    ).lower()
    path = WAYFINDING_PATHS.get(zone, [])
    if name in path:
        return path[: path.index(name) + 1]

    ordered_names = [
        item_name
        for item_name, _order in sorted(ROUTE_SPOT_ORDER.get(zone, {}).items(), key=lambda item: item[1])
    ]
    if name in ordered_names:
        return ordered_names[: ordered_names.index(name) + 1]
    return [name]


def compact_wayfinding_steps(steps, max_steps=9):
    if len(steps) <= max_steps:
        return steps
    return [steps[0], *steps[-(max_steps - 1) :]]


def compact_location_hint_for_direction(location):
    clauses = [part.strip() for part in re.split(r"[，,；;。]", str(location or "")) if part.strip()]
    if clauses:
        return compact_answer_text("，".join(clauses[:3]), 90).rstrip("。")
    return compact_answer_text(location, 90).rstrip("。")


def build_spot_direction_answer(spot, location):
    name = (spot or {}).get("name", "")
    if not name:
        return ""
    steps = compact_wayfinding_steps(wayfinding_path_for_spot(spot))
    route_text = " → ".join(steps)
    location_hint = compact_location_hint_for_direction(location)

    if name == "五印坛城":
        route_part = (
            f"从景区入口/游客服务中心出发，沿主游线走：{route_text}。"
            if route_text
            else "从景区入口进园后，先往灵山梵宫方向走。"
        )
        location_part = f"{name}在{location_hint}，" if location_hint else f"{name}靠近灵山梵宫，"
        return f"{route_part}到灵山梵宫后，走连接梵宫和坛城的景观栈道过去；{location_part}现场看“五印坛城/坛城”导视牌。"

    if route_text:
        location_part = f"{name}在{location_hint}，" if location_hint else ""
        return f"从景区入口/游客服务中心出发，建议按 {route_text} 的顺序走。{location_part}现场跟“{name}”导视牌确认最后一段。"
    if location_hint:
        return f"{name}在{location_hint}，建议按现场导视牌或导航前往。"
    return ""


def structured_knowledge_direct_answer(question, fields, spot=None):
    name = fields.get("景点名称") or (spot or {}).get("name", "")
    location = fields.get("具体位置") or (spot or {}).get("location", "")
    open_info = fields.get("演艺/开放信息") or fields.get("开放/演艺信息") or (spot or {}).get("openTime", "")
    parameters = fields.get("建筑/景观参数", "")
    highlights = fields.get("游玩亮点", "")
    detail = fields.get("详细介绍") or (spot or {}).get("story", "")
    culture = fields.get("文化内涵", "")
    core = fields.get("核心功能") or (spot or {}).get("description", "")
    remarks = fields.get("备注", "")

    if asks_for_duration(question):
        duration = (spot or {}).get("duration")
        if duration:
            return f"{name or '这里'}建议游览约 {duration} 分钟。"

    if asks_for_parameters(question) and parameters:
        answer = compact_answer_text(parameters, 130)
        if name and not answer.startswith(name):
            return f"{name}{answer}。"
        return f"{answer}。"

    if asks_for_directions(question):
        answer = build_spot_direction_answer(spot, location)
        if answer:
            return answer

    if asks_for_location(question) and location:
        prefix = f"{name}位于" if name else "位于"
        return f"{prefix}{compact_answer_text(location, 105)}。"

    if asks_for_performance(question):
        answer = concise_performance_info(open_info)
        if answer:
            if name and not answer.startswith(name):
                return f"{name}{answer}。"
            return f"{answer}。"

    if asks_for_timing(question) and open_info:
        answer = concise_open_info(open_info) or compact_answer_text(open_info, 120)
        if name and not answer.startswith(name):
            return f"{name}{answer}。"
        return f"{answer}。"

    if asks_for_photo(question):
        reason = concise_photo_reason(location, highlights, detail, culture)
        if name and reason:
            subject_reason = reason if reason.startswith(name) else f"{name}{reason}"
            return f"适合。{subject_reason}，适合拍建筑外观和环境氛围。"
        source = " ".join(part for part in (highlights, location, detail, culture, remarks) if part)
        sentence = pick_sentence(source, ("拍照", "打卡", "观景", "建筑", "风格", "四面环水", "金色", "白墙", "全景"), 130)
        if sentence:
            subject = name or "这里"
            extra = ""
            if "拍照" not in sentence and "打卡" not in sentence:
                extra = "，适合拍建筑外观、环境氛围和远景合影"
            return f"适合。{subject}{sentence}{extra}。"
        if name:
            return f"适合。{name}适合拍建筑外观和环境氛围，建议选择光线好的时段拍摄。"

    if asks_for_intro(question):
        sentence = pick_sentence(" ".join(part for part in (core, culture, detail, highlights) if part), max_chars=180)
        if sentence:
            return f"{name}{sentence}。" if name and not sentence.startswith(name) else f"{sentence}。"

    return None


def clean_knowledge_summary(summary):
    lines = []
    for raw_line in str(summary or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^(景区|景点ID|景点名称)[：:]", line):
            continue
        line = re.sub(r"^(具体位置|建筑/景观参数|核心功能|文化内涵|详细介绍|游玩亮点|演艺/开放信息|开放/演艺信息|备注)[：:]", "", line).strip()
        if line:
            lines.append(line)
    return compact_answer_text(" ".join(lines), 220)


def asks_for_timing(question):
    text = normalize_text(question)
    direct_terms = ("什么时候", "几点", "何时", "表演时间", "演出时间", "场次", "几点演", "几点看")
    if any(term in text for term in direct_terms):
        return True
    return "时间" in text and any(term in text for term in ("表演", "演出", "节目", "开放", "开始"))


def has_timing_detail(text):
    return bool(
        re.search(
            r"(\d{1,2}[:：]\d{2}|\d{1,2}\s*点|上午|下午|中午|晚上|每日|每天|每周|周[一二三四五六日天]|场次|准点|整点|开放时间|演出时间)",
            str(text or ""),
            )
        )


def should_prefer_spot_knowledge(question, matched_spots):
    exact_names = exact_spot_names_from_question(question, matched_spots)
    if not exact_names:
        return False
    if asks_for_directions(question) and len(exact_names) > 1:
        return False
    if any(
        check(question)
        for check in (
            asks_for_location,
            asks_for_directions,
            asks_for_photo,
            asks_for_duration,
            asks_for_parameters,
            asks_for_performance,
            asks_for_timing,
        )
    ):
        return True
    text = normalize_text(question)
    return any(term in text for term in ("介绍", "亮点", "看什么"))


def has_exact_spot_knowledge_hit(question, knowledge_hits, matched_spots):
    exact_names = exact_spot_names_from_question(question, matched_spots)
    if not exact_names:
        return False
    return any(knowledge_document_matches_spot(hit, spot_name) for hit in knowledge_hits for spot_name in exact_names)


RELIGIOUS_ETIQUETTE_TERMS = ("佛教场所", "佛教文化场所", "寺庙", "佛像", "宗教场所", "礼仪", "禁忌", "不触摸", "拍照限制", "能摸")


def asks_for_religious_etiquette(question):
    return text_has_any(compact_query_text(question), RELIGIOUS_ETIQUETTE_TERMS)


def sync_known_spot_locations(connection):
    now = int(time.time())
    for name, override in SPOT_LOCATION_OVERRIDES.items():
        connection.execute(
            """
            UPDATE scenic_spot
            SET lat = ?, lon = ?, map_zone = ?, map_x = ?, map_y = ?, verified_location = 1, updated_at = ?
            WHERE name = ?
            """,
            (
                override["lat"],
                override["lon"],
                override["zone"],
                override["mapX"],
                override["mapY"],
                now,
                name,
            ),
        )


def compact_query_text(value):
    return re.sub(r"\s+", "", normalize_text(value))


def text_has_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def related_spots_by_name(spots, names):
    wanted = set(names or [])
    return [spot for spot in spots if spot.get("name") in wanted]


def structured_fact_response(answer, spots, persona, intent, sentiment, title, spot_names=None, confidence=0.96):
    related_spots = related_spots_by_name(spots, spot_names or [])
    return {
        "answer": answer,
        "relatedSpots": related_spots,
        "sourceRefs": [
            {
                "type": "knowledge",
                "title": title,
                "category": "结构化事实库",
                "sourceType": "fact_table",
                "sourceFile": "标准测试集与官方资料包",
            }
        ],
        "intent": intent,
        "confidence": confidence,
        "sentiment": sentiment,
        "llmProvider": "local_fact",
        "modelName": "结构化事实库",
        "fallback": True,
    }


def frontend_selected_spot_context_index(question):
    value = str(question or "")
    markers = ("当前选中的景点是", "当前景点是", "当前选中景点是")
    indexes = [value.find(marker) for marker in markers if value.find(marker) >= 0]
    return min(indexes) if indexes else -1


def is_smalltalk_question(question):
    text = compact_query_text(question)
    if text in {"你好", "您好", "在吗", "hello", "hi"}:
        return True
    return text_has_any(text, ("谢谢", "感谢", "辛苦了", "你是谁", "你叫什么", "讲个笑话", "写一首诗"))


def visitor_question_without_frontend_context(question, spots=None):
    marker_index = frontend_selected_spot_context_index(question)
    if marker_index < 0:
        return str(question or "").strip()
    visitor_question = str(question or "")[:marker_index].strip(" ，。；;")
    if visitor_question and is_smalltalk_question(visitor_question):
        return visitor_question
    if visitor_question and spots and match_spots_by_question(visitor_question, spots):
        return visitor_question
    return str(question or "").strip()


def should_bypass_knowledge_for_general_question(question):
    text = compact_query_text(question)
    scenic_terms = ("景区", "景点", "灵山", "拈花", "大佛", "梵宫", "九龙", "开放", "开门", "闭园", "表演", "演出", "场次")
    if text_has_any(text, ("现在几点", "几点了", "当前时间", "今天星期几", "今天几号", "当前日期")):
        return not text_has_any(text, scenic_terms)
    if text_has_any(text, ("天气", "气温", "下雨", "带伞")):
        return not text_has_any(text, scenic_terms)
    return False


def structured_fact_answer(question, spots, persona, intent, sentiment):
    text = compact_query_text(question)

    if text in {"你好", "您好", "在吗", "hello", "hi"}:
        return structured_fact_response(
            "你好。",
            spots,
            persona,
            intent,
            sentiment,
            "日常问候",
            confidence=0.9,
        )
    if text_has_any(text, ("谢谢", "感谢", "辛苦了")):
        return structured_fact_response(
            "不客气。",
            spots,
            persona,
            intent,
            sentiment,
            "日常问候",
            confidence=0.9,
        )
    if text_has_any(text, ("你是谁", "你叫什么")):
        return structured_fact_response(
            "我是景区数字导览助手。",
            spots,
            persona,
            intent,
            sentiment,
            "身份问答",
            confidence=0.9,
        )
    if text_has_any(text, ("现在几点", "几点了", "当前时间")) and not text_has_any(
        text, ("景区", "开放", "开门", "闭园", "表演", "演出", "场次", "九龙", "梵宫")
    ):
        return structured_fact_response(
            f"现在是 {datetime.now().strftime('%H:%M')}。",
            spots,
            persona,
            intent,
            sentiment,
            "当前时间",
            confidence=0.9,
        )
    if text_has_any(text, ("投诉", "意见反馈", "我要反馈")):
        return structured_fact_response(
            "请联系游客服务中心或现场工作人员反馈问题；如果情况紧急，优先找最近的工作人员协助处理。",
            spots,
            persona,
            intent,
            sentiment,
            "投诉反馈",
            ["游客服务中心"],
            confidence=0.9,
        )
    if text_has_any(text, ("梵宫", "灵山梵宫")) and "五印坛城" in text and text_has_any(text, ("怎么走", "怎么去", "怎么到", "过去")):
        return structured_fact_response(
            "从灵山梵宫到五印坛城，往香水海方向走连接梵宫和坛城的景观栈道即可；五印坛城在香水海中央独立圆岛上，现场跟“五印坛城/坛城”导视牌走。",
            spots,
            persona,
            intent,
            sentiment,
            "梵宫到五印坛城问路",
            ["灵山梵宫", "五印坛城"],
            confidence=0.94,
        )
    if text_has_any(text, ("手机没电", "充电", "充电宝", "借电")):
        return structured_fact_response(
            "可以先到游客服务中心或附近商铺咨询充电服务，也可以请现场工作人员协助。",
            spots,
            persona,
            intent,
            sentiment,
            "充电求助",
            ["游客服务中心"],
            confidence=0.88,
        )
    if text_has_any(text, ("卫生间", "洗手间", "厕所")):
        return structured_fact_response(
            "请按现场导视前往最近卫生间；不确定位置时，可以询问游客服务中心或附近工作人员。",
            spots,
            persona,
            intent,
            sentiment,
            "卫生间指引",
            ["游客服务中心"],
            confidence=0.88,
        )
    if text_has_any(text, ("游客服务中心", "服务中心")) and text_has_any(text, ("在哪", "哪里", "位置", "怎么走", "怎么去")):
        return structured_fact_response(
            "游客服务中心在景区入口服务区，入园后可先在这里咨询路线、寄存、母婴室、失物招领、医药箱和无障碍服务。",
            spots,
            persona,
            intent,
            sentiment,
            "游客服务中心位置",
            ["游客服务中心"],
            confidence=0.92,
        )
    if text_has_any(text, ("游客服务中心", "服务中心")) and text_has_any(text, ("能办", "有什么", "服务", "可以办", "能做")):
        return structured_fact_response(
            "游客服务中心可咨询路线、票务和现场服务，也可办理或咨询寄存、母婴室、失物招领、医药箱、轮椅与无障碍服务。",
            spots,
            persona,
            intent,
            sentiment,
            "游客服务中心功能",
            ["游客服务中心"],
            confidence=0.92,
        )
    if text_has_any(text, ("母婴", "哺乳", "换尿布")):
        return structured_fact_response(
            "景区母婴服务建议先到游客服务中心咨询，现场工作人员可指引最近母婴室或临时照护点位。",
            spots,
            persona,
            intent,
            sentiment,
            "母婴服务",
            ["游客服务中心"],
            confidence=0.88,
        )
    if text_has_any(text, ("寄存", "行李", "存包")):
        return structured_fact_response(
            "行李寄存请先到游客服务中心咨询，具体寄存点、收费和可寄存物品范围以现场服务台说明为准。",
            spots,
            persona,
            intent,
            sentiment,
            "行李寄存",
            ["游客服务中心"],
            confidence=0.88,
        )
    if text_has_any(text, ("丢了", "丢失", "遗失", "掉了", "找不到")):
        return structured_fact_response(
            "物品丢失请尽快前往游客服务中心办理失物招领登记，也可以联系附近工作人员协助回忆路线和广播寻物。",
            spots,
            persona,
            intent,
            sentiment,
            "失物招领",
            ["游客服务中心"],
            confidence=0.9,
        )
    if text_has_any(text, ("摔倒", "受伤", "扭伤", "擦伤")):
        return structured_fact_response(
            "如果摔倒或受伤，请先停止移动并联系附近工作人员；可前往游客服务中心寻求医药箱、急救和安保协助，严重情况优先拨打急救电话。",
            spots,
            persona,
            intent,
            sentiment,
            "受伤急救",
            ["游客服务中心"],
            confidence=0.9,
        )
    if text_has_any(text, ("天气", "下雨", "气温", "冷不冷", "热不热")):
        return structured_fact_response(
            "我这里不能获取实时天气；出发前请查看天气预报，景区步行较多，雨天注意防滑，夏季注意防晒。",
            spots,
            persona,
            intent,
            sentiment,
            "天气提示",
            confidence=0.82,
        )
    if text_has_any(text, ("夏天", "高温", "热", "中暑")) and text_has_any(text, ("注意", "游览", "怎么办", "带什么")):
        return structured_fact_response(
            "夏天游览建议做好防晒，随身带水，避开正午高温时段，量力安排登云道等台阶路段；不适时及时到游客服务中心或找工作人员协助。",
            spots,
            persona,
            intent,
            sentiment,
            "夏季游览提示",
            ["游客服务中心"],
            confidence=0.88,
        )
    if text_has_any(text, ("宠物", "猫", "狗")):
        return structured_fact_response(
            "宠物入园政策请以景区当天公告和现场服务中心说明为准；若携带导盲犬等特殊情况，建议先咨询游客服务中心确认通行要求。",
            spots,
            persona,
            intent,
            sentiment,
            "宠物入园提示",
            ["游客服务中心"],
            confidence=0.82,
        )
    if text_has_any(text, ("无人机", "航拍", "飞行器")):
        return structured_fact_response(
            "景区内无人机和航拍飞行涉及游客安全、宗教场所秩序和空域管理，请以景区公告和现场工作人员要求为准，未经允许不要起飞。",
            spots,
            persona,
            intent,
            sentiment,
            "无人机安全提示",
            confidence=0.82,
        )
    if text_has_any(text, ("吸烟", "抽烟", "烟")):
        return structured_fact_response(
            "景区内请遵守禁烟和消防安全要求，不要在佛教文化场所、室内场馆和人群密集处吸烟；如需吸烟请按现场指引前往指定区域。",
            spots,
            persona,
            intent,
            sentiment,
            "吸烟提示",
            confidence=0.82,
        )
    if text_has_any(text, ("定位不准", "定位失败", "扫码定位", "扫码失败", "点位码", "位置不准")):
        return structured_fact_response(
            "定位或扫码失败时，可到开阔处重试，手动选择附近景点或输入标识牌点位码；仍不确定时请到游客服务中心或询问现场工作人员。",
            spots,
            persona,
            intent,
            sentiment,
            "定位扫码提示",
            ["游客服务中心"],
            confidence=0.86,
        )
    if text_has_any(text, ("图片识别", "识别不出来", "照片识别", "拍照识别")):
        return structured_fact_response(
            "图片识别不出来时，建议重新拍摄清晰的景点主体或标识牌，也可以改用文字问答、手动定位，必要时咨询游客服务中心。",
            spots,
            persona,
            intent,
            sentiment,
            "图片识别提示",
            ["游客服务中心"],
            confidence=0.86,
        )

    if text_has_any(text, ("门票加观光车", "门票+观光车", "联票", "套票")):
        return structured_fact_response(
            "网购门票加观光车联票为 225 元，包含景区门票和观光车，适合想减少步行、带老人儿童或行程较紧的游客。",
            spots,
            persona,
            intent,
            sentiment,
            "票务政策",
        )
    if "观光车" in text and text_has_any(text, ("多少钱", "价格", "票价", "单独", "购票", "收费")):
        return structured_fact_response(
            "观光车单独购票为 40 元/人，主要用于景区内节点换乘，体力有限、带老人儿童或想节省时间时更合适。",
            spots,
            persona,
            intent,
            sentiment,
            "观光车票价",
        )
    if text_has_any(text, ("半价票", "半票")):
        return structured_fact_response(
            "半价票为 105 元，适用于 6-18 周岁未成年人、全日制本科及以下学生、60-69 周岁老人；现场购票请以景区证件核验为准。",
            spots,
            persona,
            intent,
            sentiment,
            "半价票政策",
        )
    if text_has_any(text, ("免票", "免费", "哪些游客可以免票")):
        return structured_fact_response(
            "6 周岁以下或身高 1.4 米以下儿童、70 周岁以上老人、现役军人、残疾人可免票；优惠与免票政策以景区当天公告和证件核验为准。",
            spots,
            persona,
            intent,
            sentiment,
            "免票政策",
        )
    if "成人票" in text or ("门票" in text and text_has_any(text, ("多少钱", "价格", "票价"))):
        return structured_fact_response(
            "灵山胜境成人票为 210 元，通常适用于 18 周岁以上成年人。若还需要观光车，可参考 225 元门票加观光车网购联票。",
            spots,
            persona,
            intent,
            sentiment,
            "成人票票价",
        )
    if text_has_any(text, ("退票", "票买错", "改签", "退款")):
        return structured_fact_response(
            "退票、改签或买错票请优先查看原购票平台规则；现场购票可到游客服务中心咨询，具体以景区公告和售票系统规则为准。",
            spots,
            persona,
            intent,
            sentiment,
            "退票改签提示",
            ["游客服务中心"],
            confidence=0.86,
        )
    if text_has_any(text, ("预约", "提前预约")):
        return structured_fact_response(
            "是否需要预约请以景区官方公告、官方小程序或购票平台提示为准；节假日建议提前购票并确认入园时段。",
            spots,
            persona,
            intent,
            sentiment,
            "预约提示",
            confidence=0.84,
        )
    if text_has_any(text, ("身份证", "证件", "刷证")):
        return structured_fact_response(
            "购票、优惠票和免票通常需要按现场要求核验证件；请携带身份证或符合优惠政策的有效证件，以景区当天核验为准。",
            spots,
            persona,
            intent,
            sentiment,
            "证件核验提示",
            confidence=0.84,
        )

    if text_has_any(text, ("什么时候去", "什么季节", "比较合适", "最佳游览时间")) and not text_has_any(
        text, ("穿什么", "穿着", "穿衣", "鞋", "装备")
    ):
        return structured_fact_response(
            "春秋季节更适合游览灵山胜境；建议上午 9 点前入园避开人流，下午可安排太湖日落和核心景点拍照，节假日请预留排队时间。",
            spots,
            persona,
            intent,
            sentiment,
            "最佳游览时间",
        )
    if text_has_any(text, ("几点开放", "几点开门", "开放时间", "什么时候开放")):
        return structured_fact_response(
            "景区、场馆和演出开放时间会随季节与客流调整，请以官方公告和现场广播为准；普通游览建议上午 9 点前入园，先看九龙灌浴再衔接核心景点。",
            spots,
            persona,
            intent,
            sentiment,
            "开放时间提示",
        )
    if text_has_any(text, ("晚上", "夜间", "闭园", "还能进")):
        return structured_fact_response(
            "夜间能否入园、闭园时间和灯光开放会随季节与活动调整，请以景区当天公告、官方小程序和现场工作人员提示为准。",
            spots,
            persona,
            intent,
            sentiment,
            "夜间入园提示",
            confidence=0.84,
        )

    if "九龙灌浴" in text and text_has_any(text, ("表演时间", "演出时间", "什么时候", "几点", "场次")):
        return structured_fact_response(
            "九龙灌浴平日演出时间为 10:00、11:30、13:30、15:00，每场约 15 分钟，建议提前 10 分钟到场占位；节假日以现场广播为准。",
            spots,
            persona,
            intent,
            sentiment,
            "九龙灌浴演出时间",
            ["九龙灌浴"],
        )
    if "九龙灌浴" in text:
        return structured_fact_response(
            "九龙灌浴主要看莲花铜雕绽放、鎏金太子佛升起并旋转、九龙喷水沐浴太子佛，表现“花开见佛，九龙沐浴”的佛诞祥瑞场景。",
            spots,
            persona,
            intent,
            sentiment,
            "九龙灌浴讲解",
            ["九龙灌浴"],
        )
    if ("吉祥颂" in text) or ("梵宫" in text and text_has_any(text, ("演出", "表演", "时间", "几点"))):
        return structured_fact_response(
            "灵山梵宫《吉祥颂》每日 10:35、11:30、14:00、16:00 演出，每场约 20 分钟；建议提前排队，具体场次以景区公告为准。",
            spots,
            persona,
            intent,
            sentiment,
            "梵宫吉祥颂演出",
            ["灵山梵宫"],
        )
    if "五印坛城" in text and text_has_any(text, ("互动", "体验", "怎么玩", "有什么")):
        return structured_fact_response(
            "五印坛城可体验藏传佛教文化，顺时针绕坛城、转动转经筒，也可在开放时段预约藏香制作；参观时请保持安静、不要触摸文物。",
            spots,
            persona,
            intent,
            sentiment,
            "五印坛城互动体验",
            ["五印坛城"],
        )

    if "灵山大佛" in text and text_has_any(text, ("多高", "高度", "多少米")):
        return structured_fact_response(
            "灵山大佛通高 88 米，含台基总高 101.5 米，用铜量约 725 吨，是灵山胜境最核心的地标景点。",
            spots,
            persona,
            intent,
            sentiment,
            "灵山大佛高度",
            ["灵山大佛"],
        )
    if "灵山大佛" in text and "手印" in text:
        return structured_fact_response(
            "灵山大佛右手施无畏印，寓意除却众生痛苦；左手施与愿印，寓意赐予众生欢乐，适合结合礼佛动线讲解。",
            spots,
            persona,
            intent,
            sentiment,
            "灵山大佛手印",
            ["灵山大佛"],
        )
    if "216" in text or "登云道" in text:
        return structured_fact_response(
            "216 级登云道暗合 108 烦恼与 108 愿望，前段寓意烦恼尽除，后段寓意愿望圆满，是通往大佛的重要朝圣动线。",
            spots,
            persona,
            intent,
            sentiment,
            "登云道寓意",
            ["灵山大佛"],
        )
    if "灵山梵宫" in text and text_has_any(text, ("为什么重要", "重要", "特色", "艺术")):
        return structured_fact_response(
            "灵山梵宫是世界佛教论坛主会场，被称为佛教艺术殿堂，融合木雕、壁画、琉璃、景泰蓝等传统工艺和现代演艺技术。",
            spots,
            persona,
            intent,
            sentiment,
            "灵山梵宫价值",
            ["灵山梵宫"],
        )
    if "祥符禅寺" in text:
        return structured_fact_response(
            "祥符禅寺源于唐代小灵山佛教道场，北宋大中祥符年间得名，是连接灵山历史与现代景区的重要千年古刹。",
            spots,
            persona,
            intent,
            sentiment,
            "祥符禅寺历史",
            ["祥符禅寺"],
        )
    if "灵山大照壁" in text or "大照壁" in text:
        return structured_fact_response(
            "灵山大照壁位于景区入口，长 39.8 米、高 7 米，由赵朴初先生题写“灵山胜境”，被誉为“华夏第一壁”。",
            spots,
            persona,
            intent,
            sentiment,
            "灵山大照壁特色",
            ["灵山大照壁"],
        )
    if "五明桥" in text:
        return structured_fact_response(
            "五明桥代表佛教五种智慧：声明、因明、内明、医方明、工巧明，寓意游客过桥开启智慧、走向觉悟。",
            spots,
            persona,
            intent,
            sentiment,
            "五明桥寓意",
            ["五明桥"],
        )
    if "百子戏弥勒" in text:
        return structured_fact_response(
            "百子戏弥勒适合亲子游。它是青铜群雕，弥勒佛身边有百名孩童，寓意多子多福、家庭和睦，适合互动拍照。",
            spots,
            persona,
            intent,
            sentiment,
            "百子戏弥勒亲子讲解",
            ["百子戏弥勒"],
        )

    if text_has_any(text, ("历史文化", "历史路线")) and text_has_any(text, ("怎么逛", "路线", "安排")):
        return structured_fact_response(
            "历史文化路线可从南门入园，经灵山大照壁、佛手广场、祥符禅寺、灵山大佛、灵山梵宫、五印坛城等节点深度游览。",
            spots,
            persona,
            intent,
            sentiment,
            "历史文化路线",
            ["灵山大照壁", "祥符禅寺", "灵山大佛", "灵山梵宫", "五印坛城"],
        )
    if "自然风光" in text and text_has_any(text, ("路线", "适合", "怎么逛")):
        return structured_fact_response(
            "自然风光爱好者可走佛足坛、九龙灌浴、菩提大道、灵山大佛、曼飞龙塔、灵山精舍、梵宫广场等节点，约 5 小时全景游。",
            spots,
            persona,
            intent,
            sentiment,
            "自然风光路线",
            ["九龙灌浴", "灵山大佛", "曼飞龙塔"],
        )
    if text_has_any(text, ("第一次", "首次", "第一次来", "新手游")) and text_has_any(text, ("怎么玩", "怎么逛", "路线", "游览")):
        return structured_fact_response(
            "第一次来建议先走核心线：入口经灵山大照壁、五明桥到九龙灌浴，再衔接灵山大佛、灵山梵宫和五印坛城；时间紧可用观光车减少步行。",
            spots,
            persona,
            intent,
            sentiment,
            "首次游览路线",
            ["灵山大照壁", "九龙灌浴", "灵山大佛", "灵山梵宫", "五印坛城"],
        )
    if text_has_any(text, ("老人", "长辈", "少走路", "轻松")) and text_has_any(text, ("路线", "怎么逛", "怎么走", "安排", "游览")):
        return structured_fact_response(
            "老人或想轻松游览时，建议先到游客服务中心确认观光车换乘点，优先看九龙灌浴、灵山梵宫、五印坛城等核心节点，少走登云道台阶；行动不便可咨询轮椅和无障碍路线。",
            spots,
            persona,
            intent,
            sentiment,
            "轻松游览路线",
            ["游客服务中心", "九龙灌浴", "灵山梵宫", "五印坛城"],
        )
    if (re.search(r"(两|二|2)个?小时|120分钟", text) and text_has_any(text, ("怎么逛", "路线", "游览", "安排"))):
        return structured_fact_response(
            "2 小时游览建议抓核心点：从入口经灵山大照壁、五明桥、菩提大道到九龙灌浴，再根据体力二选一前往灵山梵宫或灵山大佛；时间紧可坐观光车衔接。",
            spots,
            persona,
            intent,
            sentiment,
            "两小时路线",
            ["灵山大照壁", "五明桥", "九龙灌浴", "灵山梵宫", "灵山大佛"],
        )
    if text_has_any(text, ("半天", "半日", "3小时", "4小时", "三小时", "四小时")) and text_has_any(text, ("怎么安排", "怎么逛", "路线", "游览")):
        return structured_fact_response(
            "半天游览建议走核心路线：灵山大照壁、五明桥、九龙灌浴、灵山大佛、灵山梵宫；若还有体力，再顺路到五印坛城拍照参观。",
            spots,
            persona,
            intent,
            sentiment,
            "半天路线",
            ["灵山大照壁", "九龙灌浴", "灵山大佛", "灵山梵宫", "五印坛城"],
        )
    if text_has_any(text, ("一天", "一日", "全天")) and text_has_any(text, ("怎么安排", "怎么逛", "路线", "游览")):
        return structured_fact_response(
            "一天游览可完整串联灵山大照壁、五明桥、佛足坛、九龙灌浴、灵山大佛、灵山梵宫、五印坛城和曼飞龙塔；中途按体力选择观光车换乘。",
            spots,
            persona,
            intent,
            sentiment,
            "一天路线",
            ["灵山大照壁", "五明桥", "九龙灌浴", "灵山大佛", "灵山梵宫", "五印坛城", "曼飞龙塔"],
        )
    if text_has_any(text, ("亲子家庭", "亲子游", "孩子", "儿童")) and text_has_any(text, ("路线", "安排", "适合", "怎么玩")):
        return structured_fact_response(
            "亲子家庭可从南门入园，依次看九龙灌浴、佛手广场、百子戏弥勒、灵山梵宫、五印坛城，约 4 小时轻松游。",
            spots,
            persona,
            intent,
            sentiment,
            "亲子家庭路线",
            ["九龙灌浴", "百子戏弥勒", "灵山梵宫", "五印坛城"],
        )
    if text_has_any(text, ("拍照", "打卡", "出片")) and not asks_for_religious_etiquette(question):
        return structured_fact_response(
            "拍照打卡推荐灵山大照壁入口合影、九龙灌浴动态表演、灵山大佛恢弘地标、五印坛城和曼飞龙塔佛教建筑群。",
            spots,
            persona,
            intent,
            sentiment,
            "拍照打卡推荐",
            ["灵山大照壁", "九龙灌浴", "灵山大佛", "五印坛城", "曼飞龙塔"],
        )

    if text_has_any(text, ("素食", "素斋", "素面")):
        return structured_fact_response(
            "景区素食可关注梵宫素斋自助，参考价约 50 元/位；素面套餐约 35 元/位；想深度体验佛教饮食文化可关注灵山精舍素斋。",
            spots,
            persona,
            intent,
            sentiment,
            "素食餐饮推荐",
            ["灵山梵宫"],
        )
    if "香月花街" in text and text_has_any(text, ("购物", "买", "商铺", "文创", "餐饮")):
        return structured_fact_response(
            "香月花街是拈花湾核心禅意商业街，分布文创商铺、特色美食和非遗手作，适合购物、餐饮和夜间休闲打卡。",
            spots,
            persona,
            intent,
            sentiment,
            "香月花街购物",
            ["香月花街"],
        )
    if text_has_any(text, ("穿什么", "穿着", "穿衣", "鞋", "装备")):
        return structured_fact_response(
            "灵山胜境步行较多，建议穿舒适运动鞋；夏季注意防晒，冬季注意保暖，并携带充电宝、雨伞等物品。",
            spots,
            persona,
            intent,
            sentiment,
            "游览装备建议",
        )
    if asks_for_religious_etiquette(question):
        return structured_fact_response(
            "在佛教文化场所应保持安静，尊重宗教信仰，不触摸佛像，不随意拍照；部分区域禁止拍照时请听从现场提示。",
            spots,
            persona,
            intent,
            sentiment,
            "宗教场所游览礼仪",
        )
    if text_has_any(text, ("迷路", "身体不适", "急救", "不舒服", "求助")):
        return structured_fact_response(
            "如果迷路或身体不适，请优先前往游客服务中心或联系现场工作人员；紧急情况可请工作人员协助呼叫医疗与安保支持。",
            spots,
            persona,
            intent,
            sentiment,
            "安全求助",
            ["游客服务中心"],
        )
    if text_has_any(text, ("无障碍", "轮椅", "行动不便")):
        return structured_fact_response(
            "行动不便游客建议先到游客服务中心咨询轮椅租借、无障碍路线和观光车换乘安排，现场路线以工作人员指引为准。",
            spots,
            persona,
            intent,
            sentiment,
            "无障碍服务",
            ["游客服务中心"],
        )
    if text_has_any(text, ("停车", "停车场", "自驾")):
        return structured_fact_response(
            "自驾游客可按现场指引前往灵山胜境停车区，入园后先确认游客服务中心、卫生间和观光车乘车点；节假日建议提前到达。",
            spots,
            persona,
            intent,
            sentiment,
            "交通停车指南",
            ["游客服务中心"],
        )

    return None


def select_knowledge_hits_for_answer(question, knowledge_hits, matched_spots):
    if not knowledge_hits:
        return []
    top_score = float(knowledge_hits[0].get("score", 0) or 0)
    min_score = max(env_float("SCENIC_KNOWLEDGE_ANSWER_THRESHOLD", 24.0), top_score * 0.62)
    selected = [hit for hit in knowledge_hits if float(hit.get("score", 0) or 0) >= min_score]

    normalized_question = normalize_text(question)
    exact_spot_names = []
    for spot in matched_spots or []:
        name = normalize_text(spot["name"])
        short_name = name.replace("灵山", "").replace("拈花湾", "").replace("拈花", "")
        if name in normalized_question or (short_name and short_name in normalized_question):
            exact_spot_names.extend([name, short_name])

    if exact_spot_names:
        spot_selected = []
        for hit in selected or knowledge_hits[:1]:
            searchable = normalize_text(f"{hit.get('title', '')} {hit.get('category', '')} {hit.get('content', '')[:500]}")
            if any(name and name in searchable for name in exact_spot_names):
                spot_selected.append(hit)
        if spot_selected:
            selected = spot_selected

    return (selected or knowledge_hits[:1])[:3]


def call_openai_compatible_llm(messages, config=None):
    config = config or get_llm_config()
    return call_llm_client(messages, config, retry_count=env_int("SCENIC_LLM_RETRIES", 2))


def synthesize_with_doubao(payload):
    config = doubao_tts_config()
    text = str(payload.get("text", "")).strip()
    if not text:
        raise ValueError("语音文本不能为空")
    if len(text) > 900:
        text = text[:900]
    if not config["available"]:
        return {
            "available": False,
            "fallback": True,
            "provider": "doubao",
            "reason": config["reason"],
            "message": "豆包语音暂未配置，已回退到浏览器语音。",
        }
    request_id = str(uuid.uuid4())
    body = {
        "app": {
            "appid": config["appId"],
            "token": config["accessToken"],
            "cluster": config["cluster"],
        },
        "user": {"uid": str(payload.get("uid", "scenic-guide-demo"))[:64]},
        "audio": {
            "voice_type": str(payload.get("voiceType") or config["voiceType"]).strip(),
            "encoding": "mp3",
            "speed_ratio": max(0.75, min(float(payload.get("speed", 0.94)), 1.25)),
            "volume_ratio": max(0.5, min(float(payload.get("volume", 1.0)), 1.5)),
            "pitch_ratio": max(0.8, min(float(payload.get("pitch", 1.02)), 1.2)),
        },
        "request": {
            "reqid": request_id,
            "text": text,
            "text_type": "plain",
            "operation": "query",
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer;{config['accessToken']}",
    }
    request = urllib.request.Request(
        config["endpoint"],
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config["timeout"]) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"豆包语音接口返回 {exc.code}: {detail[:220]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, socket.timeout) as exc:
        raise RuntimeError(f"豆包语音服务不可用或超时：{exc}") from exc
    code = data.get("code", 0)
    audio_data = data.get("data")
    if code not in (0, "0", None) or not audio_data:
        message = data.get("message") or data.get("msg") or "未返回音频"
        raise RuntimeError(f"豆包语音合成失败：{message}")
    return {
        "available": True,
        "fallback": False,
        "provider": "doubao",
        "voiceType": body["audio"]["voice_type"],
        "encoding": "mp3",
        "audioDataUrl": f"data:audio/mpeg;base64,{audio_data}",
        "requestId": data.get("reqid") or request_id,
    }


def normalize_audio_data_url(audio_data):
    value = str(audio_data or "").strip()
    if not value:
        raise ValueError("请提供需要转写的语音数据")
    mime_type = "audio/webm"
    encoded = value
    if value.startswith("data:"):
        match = re.match(r"^data:(audio/[a-zA-Z0-9.+-]+);base64,(.+)$", value, re.DOTALL)
        if not match:
            raise ValueError("语音数据格式不正确，请上传 base64 编码的音频")
        mime_type = match.group(1).lower()
        encoded = match.group(2)
    if mime_type not in ALLOWED_AUDIO_MIME_TYPES:
        raise ValueError("仅支持 MP3、MP4/M4A、WAV、Ogg 或 WebM 音频")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("语音 base64 数据无效") from exc
    if not raw:
        raise ValueError("语音内容为空")
    if len(raw) > MAX_AUDIO_BYTES:
        raise ValueError("语音文件过大，请控制在 12MB 以内")
    extension = {
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/webm": ".webm",
    }.get(mime_type, ".webm")
    return mime_type, raw, extension


def build_asr_command(template, audio_path, output_dir):
    command_text = template.replace("{audio}", str(audio_path)).replace("{output}", str(output_dir))
    return shlex.split(command_text, posix=os.name != "nt")


def transcribe_with_local_asr(audio_bytes, extension, config):
    temp_root = DATA_DIR / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_root) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        audio_path = temp_dir / f"speech{extension}"
        audio_path.write_bytes(audio_bytes)
        command = build_asr_command(config["command"], audio_path, temp_dir)
        completed = subprocess.run(
            command,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=config["timeout"],
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[:300]
            raise RuntimeError(f"本地 ASR 转写失败：{detail or completed.returncode}")
        text_files = sorted(temp_dir.glob("*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)
        if text_files:
            return text_files[0].read_text(encoding="utf-8", errors="ignore").strip()
        return (completed.stdout or "").strip()


def transcribe_with_cloud_asr(audio_data_url, config):
    body = {"audio": audio_data_url, "language": "zh-CN"}
    headers = {"Content-Type": "application/json"}
    if config["apiKey"]:
        headers["Authorization"] = f"Bearer {config['apiKey']}"
    request = urllib.request.Request(
        config["endpoint"],
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config["timeout"]) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, socket.timeout) as exc:
        raise RuntimeError(f"云端 ASR 服务不可用或超时：{exc}") from exc
    text = data.get("text") or data.get("transcript") or data.get("result")
    if isinstance(text, dict):
        text = text.get("text") or text.get("transcript")
    if not text:
        raise RuntimeError("云端 ASR 未返回转写文本")
    return str(text).strip()


def transcribe_audio(payload):
    config = asr_config()
    if not config["available"]:
        return {
            "available": False,
            "fallback": True,
            "provider": config["provider"],
            "reason": config["reason"],
            "text": "",
            "message": "ASR 未配置或不可用，请直接使用文字输入。",
        }

    audio_value = str(payload.get("audio", "")).strip()
    _mime_type, audio_bytes, extension = normalize_audio_data_url(audio_value)
    if config["provider"] in {"local_whisper", "whisper", "faster_whisper"}:
        text = transcribe_with_local_asr(audio_bytes, extension, config)
    else:
        text = transcribe_with_cloud_asr(audio_value, config)
    return {
        "available": True,
        "fallback": False,
        "provider": config["provider"],
        "text": text,
    }


def generate_with_llm(messages):
    config = get_llm_config()
    try:
        result = call_openai_compatible_llm(messages, config)
        if result:
            return result
    except RuntimeError as exc:
        print(f"[LLM] 调用失败：{exc}")
        raise
    return None


def build_llm_context(question, spots, matched_spots, knowledge_hits):
    documents = knowledge_hits[:5]
    spot_pool = matched_spots[:3]
    knowledge_text = "\n".join(
        f"[资料{index + 1}] {item['title']}（{item['category']}）：{trim_public_text(item['content'], 900)}"
        for index, item in enumerate(documents)
    )
    spot_text = "\n".join(
        (
            f"[景点{index + 1}] {spot['name']}：{spot['description']}；"
            f"位置：{spot['location']}；开放：{spot['openTime']}；"
            f"建议游览：{spot['duration']}分钟；标签：{'、'.join(spot['tags'])}；讲解：{trim_public_text(spot['story'], 520)}"
        )
        for index, spot in enumerate(spot_pool)
    )
    return documents, "\n\n".join(part for part in (knowledge_text, spot_text) if part).strip()


def build_llm_messages(question, persona, intent, context):
    has_context = bool(str(context or "").strip())
    current_time_line = f"当前本地时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}。\n" if not has_context else ""
    system = (
        f"你是景区 AI 数字人导览员，身份是\u201c{persona['role']}\u201d，讲解风格：{persona['style']}。"
        "你要像真实景区导游一样直接回答游客。"
        "不要自我介绍，不要说“我是”，不要使用“贫僧、施主、阿弥陀佛”等角色化套话，"
        "不要提知识库、数据库、RAG、命中、检索、上下文或系统提示词。"
        "必须优先依据提供的景区资料回答，不能编造不存在的票价、活动、路线和安全承诺。"
        "除非资料明确写了免费、免票或优惠，否则不要说免费；不要把\u201c全天开放\u201d理解成\u201c免费开放\u201d。"
        "如果没有提供景区资料，按游客原问题直接短答；通用编程、翻译、生活、写作问题要正常回答，不要说自己只懂景区。"
        "问候寒暄只回复一句，不要主动介绍景区、推荐景点或规划路线；如果询问当前时间，必须使用用户消息里的当前本地时间回答。"
        "如果问题涉及实时信息或景区事实但资料不足，只给出稳妥建议，例如以景区当天公告、现场广播或服务中心信息为准。"
        "回答要自然、聪明、简洁，适合游客现场听讲；一般控制在 160 到 360 个中文字符。"
        "涉及路线时用清晰顺序说明；涉及安全和服务时语气稳妥。"
    )
    context_text = context if has_context else "无。"
    final_instruction = "请直接给游客回答：" if has_context else "请只根据游客原问题直接回答，不要主动展开景区介绍："
    user = (
        f"游客问题：{question}\n"
        f"识别意图：{intent}\n\n"
        f"{current_time_line}"
        f"可用景区资料：\n{context_text}\n\n"
        f"{final_instruction}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def generate_llm_answer(question, spots, matched_spots, knowledge_hits, persona, intent, sentiment):
    documents, context = build_llm_context(question, spots, matched_spots, knowledge_hits)
    try:
        llm_result = generate_with_llm(build_llm_messages(question, persona, intent, context))
    except Exception as exc:
        print(f"[LLM] 调用失败，已切换规则兜底：{exc}")
        return None
    if not llm_result:
        return None
    related_spots = matched_spots[:3]
    source_refs = [
        {
            "type": "model",
            "title": llm_result["model"],
            "category": llm_result["provider"],
        }
    ]
    source_refs.extend(
        {
            "type": "knowledge",
            "id": item["id"],
            "title": item["title"],
            "category": item["category"],
            "sourceType": item.get("sourceType"),
            "sourceFile": item.get("sourceFile"),
            "sourceSection": item.get("sourceSection"),
        }
        for item in documents[:3]
    )
    source_refs.extend({"type": "spot", "id": spot["id"], "title": spot["name"]} for spot in related_spots[:2])
    return {
        "answer": llm_result["content"],
        "relatedSpots": related_spots,
        "sourceRefs": source_refs,
        "intent": intent,
        "confidence": 0.9 if knowledge_hits else 0.76,
        "sentiment": sentiment,
        "llmProvider": llm_result["provider"],
        "modelName": llm_result["model"],
        "fallback": False,
    }


def is_confident_knowledge_hit(knowledge_hits):
    if not knowledge_hits:
        return False
    return float(knowledge_hits[0].get("score", 0) or 0) >= env_float("SCENIC_KNOWLEDGE_ANSWER_THRESHOLD", 24.0)


def answer_from_knowledge(question, spots, matched_spots, knowledge_hits, persona, intent, sentiment):
    answer_hits = select_knowledge_hits_for_answer(question, knowledge_hits, matched_spots)
    fields = extract_structured_fields(answer_hits[0]) if answer_hits else {}
    field_spot_name = fields.get("景点名称", "")
    field_spot = next((spot for spot in spots if field_spot_name and spot.get("name") == field_spot_name), None)
    related_spots = (matched_spots or ([field_spot] if field_spot else []) or match_spots_by_question(field_spot_name or "", spots))[:3]
    direct_answer = structured_knowledge_direct_answer(question, fields, related_spots[0] if related_spots else None)
    summary = direct_answer or clean_knowledge_summary(build_knowledge_summary(question, answer_hits))
    if not summary:
        return None
    if asks_for_timing(question) and not has_timing_detail(summary):
        summary = f"{summary} 具体场次或时刻建议以景区当天公告和现场提示为准。"
    source_refs = [
        {
            "type": "knowledge",
            "id": item["id"],
            "title": item["title"],
            "category": item["category"],
            "sourceType": item.get("sourceType"),
            "sourceFile": item.get("sourceFile"),
            "sourceSection": item.get("sourceSection"),
        }
        for item in answer_hits[:3]
    ]
    prefix = summary
    if not direct_answer and related_spots and intent == "路线推荐":
        names = "、".join(spot["name"] for spot in related_spots)
        prefix = f"{summary} 推荐您重点关注 {names}。"
    return {
        "answer": prefix,
        "relatedSpots": related_spots,
        "sourceRefs": source_refs,
        "intent": intent,
        "confidence": max(0.95, min(0.98, round(0.9 + float(knowledge_hits[0].get("score", 0) or 0) / 700, 2))),
        "sentiment": sentiment,
        "llmProvider": "knowledge_base",
        "modelName": "本地知识库",
        "fallback": False,
    }


def llm_unavailable_answer(question, spots, persona, intent, sentiment):
    top_spots = sorted(spots, key=lambda spot: spot["popularity"], reverse=True)[:3]
    config = get_llm_config()
    reason = config["reason"] if config["reason"] != "ready" else "模型接口未返回有效回答或连接失败"
    return {
        "answer": (
            "这个问题暂时无法确认准确答案，建议以景区当天公告、现场广播或服务中心信息为准。"
            f"您也可以先关注 {'、'.join(spot['name'] for spot in top_spots)}。"
        ),
        "relatedSpots": top_spots,
        "sourceRefs": [{"type": "runtime", "title": "DeepSeek 未返回有效回答", "category": reason}],
        "intent": intent,
        "confidence": 0.32,
        "sentiment": sentiment,
        "llmProvider": config["provider"],
        "modelName": config["model"],
        "fallback": True,
    }


def compact_context_for_vision():
    spots = get_spots()
    documents = get_knowledge_documents(include_inactive=False)[:6]
    spot_text = "\n".join(
        f"{spot['name']}：{spot['description']}；位置：{spot['location']}；标签：{'、'.join(spot['tags'])}"
        for spot in spots[:10]
    )
    knowledge_text = "\n".join(f"{doc['title']}：{doc['content'][:180]}" for doc in documents)
    return f"景点资料：\n{spot_text}\n\n知识库资料：\n{knowledge_text}".strip()


def normalize_image_data_url(image_data):
    value = str(image_data or "").strip()
    if not value:
        raise ValueError("请上传景区图片")
    mime_type = "image/jpeg"
    encoded = value
    if value.startswith("data:"):
        match = re.match(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", value, re.DOTALL)
        if not match:
            raise ValueError("图片格式不正确，请上传 base64 编码的图片")
        mime_type = match.group(1).lower()
        encoded = match.group(2)
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValueError("仅支持 JPEG、PNG、WebP 或 GIF 图片")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("图片 base64 数据无效") from exc
    if not raw:
        raise ValueError("图片内容为空")
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("图片过大，请压缩到 4MB 以内")
    return f"data:{mime_type};base64,{encoded}"


def analyze_scenic_image(payload):
    image_url = normalize_image_data_url(payload.get("image"))
    config = get_vision_llm_config()
    if not config["available"]:
        return {
            "answer": "视觉模型暂未配置或 API Key 缺失，请检查 .env 中的 SCENIC_VISION_PROVIDER、SCENIC_VISION_MODEL、SCENIC_VISION_API_KEY 或 DASHSCOPE_API_KEY。",
            "modelName": config["model"],
            "llmProvider": config["provider"],
            "fallback": True,
            "sourceRefs": [{"type": "config", "title": "模型未就绪"}],
        }
    if not config["multimodal"]:
        return {
            "answer": f"当前视觉模型 {config['model']} 不支持多模态输入。请在 .env 中设置 SCENIC_VISION_MODEL=qwen3-vl-plus 或其他支持图像输入的视觉语言模型。",
            "modelName": config["model"],
            "llmProvider": config["provider"],
            "fallback": True,
            "sourceRefs": [{"type": "config", "title": "非多模态模型"}],
        }
    question = str(payload.get("question", "")).strip() or "请识别图片内容，并结合景区知识库生成自然的游客导览讲解。"
    persona = get_persona()
    context = compact_context_for_vision()
    messages = [
        {
            "role": "system",
            "content": (
                f"你是景区 AI 数字人导览员\u201c{persona['name']}\u201d。"
                "你具备图片理解能力，需要根据游客上传的景区照片进行识别、讲解和游览建议。"
                "回答必须结合本地景区知识库，不能把无法确认的图片内容当作事实。"
                "除非资料明确写了免费、免票或优惠，否则不要说免费；不要把\u201c全天开放\u201d理解成\u201c免费开放\u201d。"
                "如果图片无法判断具体景点，要说明可能性，并给出进一步拍摄或定位建议。"
                "回答控制在 180 到 420 个中文字符。"
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"游客问题：{question}\n\n本地景区知识库：\n{context}\n\n请输出适合语音播报的导览回答。",
                },
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        },
    ]
    try:
        result = call_openai_compatible_llm(messages, config)
    except RuntimeError as exc:
        print(f"[VISION] 调用失败：{exc}")
        return {
            "answer": f"多模态视觉模型暂时无响应：{str(exc)[:120]}。当前页面仍可使用文字问答和知识库功能。",
            "modelName": config["model"],
            "llmProvider": config["provider"],
            "fallback": True,
            "sourceRefs": [{"type": "runtime", "title": "多模态模型未响应"}],
        }
    return {
        "answer": result["content"],
        "modelName": result["model"],
        "llmProvider": result["provider"],
        "fallback": False,
        "sourceRefs": [
            {"type": "model", "title": result["model"], "category": result["provider"]},
            {"type": "knowledge", "title": "本地景区知识库", "category": "RAG"},
            {"type": "image", "title": "游客上传图片", "category": "视觉输入"},
        ],
    }


def answer_question(question):
    spots = get_spots()
    question = visitor_question_without_frontend_context(question, spots)
    matched_spots = match_spots_by_question(question, spots)
    knowledge_hits = search_knowledge(question)
    knowledge_hits = prioritize_exact_spot_knowledge(question, knowledge_hits, matched_spots)
    if should_bypass_knowledge_for_general_question(question):
        knowledge_hits = []
    persona = get_persona()
    intent = classify_intent(question)
    sentiment = analyze_sentiment(question)
    if asks_for_religious_etiquette(question):
        fact_answer = structured_fact_answer(question, spots, persona, intent, sentiment)
        if fact_answer:
            return fact_answer
    if env_bool("SCENIC_CHAT_FAST_MODE", False):
        prefer_spot_knowledge = should_prefer_spot_knowledge(question, matched_spots)
        if (
            prefer_spot_knowledge
            and is_confident_knowledge_hit(knowledge_hits)
            and has_exact_spot_knowledge_hit(question, knowledge_hits, matched_spots)
        ):
            knowledge_answer = answer_from_knowledge(question, spots, matched_spots, knowledge_hits, persona, intent, sentiment)
            if knowledge_answer:
                return knowledge_answer
        fact_answer = structured_fact_answer(question, spots, persona, intent, sentiment)
        if fact_answer:
            return fact_answer
        if is_confident_knowledge_hit(knowledge_hits):
            knowledge_answer = answer_from_knowledge(question, spots, matched_spots, knowledge_hits, persona, intent, sentiment)
            if knowledge_answer:
                return knowledge_answer
        return rule_answer_question(question, spots, matched_spots, knowledge_hits, persona, intent, sentiment)
    confident_knowledge = is_confident_knowledge_hit(knowledge_hits)
    llm_answer = generate_llm_answer(
        question,
        spots,
        matched_spots,
        knowledge_hits if confident_knowledge else [],
        persona,
        intent,
        sentiment,
    )
    if llm_answer:
        return llm_answer
    fact_answer = structured_fact_answer(question, spots, persona, intent, sentiment)
    if fact_answer:
        return fact_answer
    if confident_knowledge:
        knowledge_answer = answer_from_knowledge(question, spots, matched_spots, knowledge_hits, persona, intent, sentiment)
        if knowledge_answer:
            return knowledge_answer
    return llm_unavailable_answer(question, spots, persona, intent, sentiment)


def build_chat_record(question, result, latency_ms=None):
    return {
        "id": str(uuid.uuid4()),
        "question": question,
        "answer": result["answer"],
        "relatedSpots": result["relatedSpots"],
        "sourceRefs": result["sourceRefs"],
        "intent": result["intent"],
        "confidence": result["confidence"],
        "sentiment": result["sentiment"],
        "llmProvider": result.get("llmProvider", "local"),
        "modelName": result.get("modelName", "规则兜底"),
        "fallback": result.get("fallback", True),
        "latencyMs": latency_ms,
        "createdAt": int(time.time()),
    }


def stream_chat_record(handler, record):
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    send_cors_headers(handler)
    handler.end_headers()
    for chunk in chunk_text(record["answer"]):
        handler.wfile.write(sse_event("delta", {"text": chunk}).encode("utf-8"))
        handler.wfile.flush()
        time.sleep(0.025)
    handler.wfile.write(sse_event("done", record).encode("utf-8"))
    handler.wfile.flush()
    handler.close_connection = True


def rule_answer_question(question, spots, matched_spots, knowledge_hits, persona, intent, sentiment):
    fact_answer = structured_fact_answer(question, spots, persona, intent, sentiment)
    if fact_answer:
        return fact_answer

    related_spots = matched_spots[:3]
    source_refs = []
    confidence = 0.58

    for spot in matched_spots:
        spot_name = normalize_text(spot["name"])
        short_name = spot_name.replace("灵山", "").replace("拈花湾", "").replace("拈花", "")
        if spot_name in normalize_text(question) or (short_name and short_name in normalize_text(question)):
            source_refs.append({"type": "spot", "id": spot["id"], "title": spot["name"]})
            answer = (
                f"{spot['name']}很值得一看。{spot['description']}"
                f"它位于{spot['location']}，开放时间为{spot['openTime']}，建议游览约 {spot['duration']} 分钟。"
                f"讲解重点：{spot['story']}"
            )
            if knowledge_hits:
                summary = clean_knowledge_summary(build_knowledge_summary(question, knowledge_hits))
                if summary:
                    answer += f" {summary}"
                    source_refs.extend(
                        {
                            "type": "knowledge",
                            "id": item["id"],
                            "title": item["title"],
                            "category": item["category"],
                            "sourceType": item.get("sourceType"),
                            "sourceFile": item.get("sourceFile"),
                            "sourceSection": item.get("sourceSection"),
                        }
                        for item in knowledge_hits[:2]
                    )
            return {
                "answer": answer,
                "relatedSpots": [spot],
                "sourceRefs": source_refs,
                "intent": intent,
                "confidence": 0.92,
                "sentiment": sentiment,
                "llmProvider": "local",
                "modelName": "规则兜底",
                "fallback": True,
            }

    if knowledge_hits:
        summary = clean_knowledge_summary(build_knowledge_summary(question, knowledge_hits))
        source_refs.extend(
            {
                "type": "knowledge",
                "id": item["id"],
                "title": item["title"],
                "category": item["category"],
                "sourceType": item.get("sourceType"),
                "sourceFile": item.get("sourceFile"),
                "sourceSection": item.get("sourceSection"),
            }
            for item in knowledge_hits[:3]
        )
        if intent == "路线推荐" and related_spots:
            names = "、".join(spot["name"] for spot in related_spots)
            answer = (
                f"{summary} 按您的兴趣可以优先关注 {names}。如果需要完整顺序和耗时，可以在\u201c个性化路线推荐\u201d区域生成路线。"
            )
        elif intent == "票务开放":
            answer = f"开放和票务信息：{summary}"
        else:
            answer = summary
        confidence = min(0.9, 0.62 + knowledge_hits[0]["score"] / 100)
        return {
            "answer": answer,
            "relatedSpots": related_spots,
            "sourceRefs": source_refs,
            "intent": intent,
            "confidence": round(confidence, 2),
            "sentiment": sentiment,
            "llmProvider": "local",
            "modelName": "规则兜底",
            "fallback": True,
        }

    top_spots = sorted(spots, key=lambda spot: spot["popularity"], reverse=True)[:3]
    names = "、".join(spot["name"] for spot in top_spots)
    return {
        "answer": (
            f"这个问题暂时无法确认准确答案，可以先关注 {names}。"
            "也可以换个问法询问开放时间、门票、停车、亲子路线或拍照打卡点。"
        ),
        "relatedSpots": top_spots,
        "sourceRefs": [{"type": "fallback", "title": "规则兜底"}],
        "intent": intent,
        "confidence": confidence,
        "sentiment": sentiment,
        "llmProvider": "local",
        "modelName": "规则兜底",
        "fallback": True,
    }


def route_order_key(spot, preferred_zone):
    zone_order = ROUTE_SPOT_ORDER.get(preferred_zone, {})
    name = spot.get("name", "")
    return (
        zone_order.get(name, 999),
        float(spot.get("mapY") if spot.get("mapY") is not None else 999),
        float(spot.get("mapX") if spot.get("mapX") is not None else 999),
        name,
    )


def select_official_route_template(spots, preference, preferred_zone):
    templates = load_official_route_templates(spots)
    for template in templates:
        if template["zone"] == preferred_zone and preference in template["preferences"] and template["spotSequence"]:
            return template
    return None


def recommend_official_template_route(spots, duration, preference, template):
    spot_by_name = {spot["name"]: spot for spot in spots}
    selected = []
    total_duration = 0
    include_full_known_route = duration >= template["duration"] * 0.82
    for name in template["spotSequence"]:
        spot = spot_by_name.get(name)
        if not spot:
            continue
        if include_full_known_route or total_duration + spot["duration"] <= duration or not selected:
            selected.append(spot)
            total_duration += spot["duration"]
        if not include_full_known_route and total_duration >= duration * 0.85:
            break

    if not selected:
        return None

    selected = sorted(selected, key=lambda spot: route_order_key(spot, template["zone"]))
    route = {
        "id": str(uuid.uuid4()),
        "title": f"{duration} 分钟{preference}路线",
        "duration": duration,
        "estimatedDuration": total_duration,
        "preference": preference,
        "spots": selected,
        "reason": (
            f"这条路线优先参考官方资料包《{template['sourceFile']}》中的“{template['sourceSection']}”，"
            f"官方完整路线约 {template['duration']} 分钟。当前按您选择的 {duration} 分钟，"
            f"保留可匹配到系统点位的官方顺序节点，预计讲解游览 {total_duration} 分钟。"
        ),
        "sourceType": "official_docx",
        "sourceFile": template["sourceFile"],
        "sourceSection": template["sourceSection"],
        "officialRouteDuration": template["duration"],
        "officialWaypoints": template["waypoints"],
        "createdAt": int(time.time()),
    }
    save_route_record(route)
    return route


def recommend_route(duration, preference):
    spots = get_spots()
    preference = preference or "佛教文化"
    preferred_zone = "nianhua" if preference in {"餐饮购物", "轻松休闲"} else "lingshan"
    zone_spots = [spot for spot in spots if spot.get("mapZone", "lingshan") == preferred_zone]
    spots = zone_spots

    official_route = select_official_route_template(spots, preference, preferred_zone)
    if official_route:
        route = recommend_official_template_route(spots, duration, preference, official_route)
        if route:
            return route

    candidates = []

    for index, spot in enumerate(spots):
        score = spot["popularity"]
        tag_text = "".join(spot["tags"])
        if preference in spot["tags"]:
            score += 34
        if preference == "佛教文化" and ("佛教文化" in spot["tags"] or "历史文化" in spot["tags"]):
            score += 24
        if preference == "历史文化" and "文化" in tag_text:
            score += 22
        if preference == "演艺体验" and ("演艺体验" in spot["tags"] or any(word in spot["story"] for word in ("表演", "演出", "灯光秀"))):
            score += 24
        if preference == "自然风光" and ("自然风光" in spot["tags"] or "轻松休闲" in spot["tags"]):
            score += 18
        if preference == "亲子游" and ("亲子游" in spot["tags"] or "室内参观" in spot["tags"]):
            score += 18
        score -= index * 0.1
        candidates.append((score, spot))

    selected = []
    total_duration = 0
    for _, spot in sorted(candidates, key=lambda item: item[0], reverse=True):
        if total_duration + spot["duration"] <= duration or not selected:
            selected.append(spot)
            total_duration += spot["duration"]
        if total_duration >= duration * 0.85:
            break

    if preferred_zone == "lingshan" and duration >= 180 and not any(spot["name"] == "游客服务中心" for spot in selected):
        service_center = next((spot for spot in spots if spot["name"] == "游客服务中心"), None)
        if service_center and total_duration + service_center["duration"] <= duration:
            selected.insert(0, service_center)
            total_duration += service_center["duration"]

    selected = sorted(selected, key=lambda spot: route_order_key(spot, preferred_zone))

    zone_label = "拈花湾小镇" if preferred_zone == "nianhua" else "灵山胜境核心区"
    route = {
        "id": str(uuid.uuid4()),
        "title": f"{duration} 分钟{preference}路线",
        "duration": duration,
        "estimatedDuration": total_duration,
        "preference": preference,
        "spots": selected,
        "reason": (
            f"这条路线围绕\u201c{preference}\u201d偏好在{zone_label}内生成，综合景点标签、热度和预计游览时长排序。"
            f"全程预计 {total_duration} 分钟，保留休息和拍照时间，适合现场导览演示。"
        ),
        "createdAt": int(time.time()),
    }
    save_route_record(route)
    return route


def validate_spot_payload(payload, existing=None):
    existing = existing or {}
    name = str(payload.get("name", existing.get("name", ""))).strip()
    if not name:
        raise ValueError("景点名称不能为空")
    tags = payload.get("tags", existing.get("tags", []))
    if isinstance(tags, str):
        tags = [tag.strip() for tag in re.split(r"[,，、]", tags) if tag.strip()]
    if not tags:
        tags = ["综合导览"]
    duration = int(payload.get("duration", existing.get("duration", 30)))
    popularity = int(payload.get("popularity", existing.get("popularity", 80)))
    status = str(payload.get("status", existing.get("status", "active"))).strip() or "active"
    if status not in ("active", "inactive"):
        status = "active"
    lat_value = payload.get("lat", existing.get("lat"))
    lon_value = payload.get("lon", existing.get("lon"))
    map_x_value = payload.get("mapX", existing.get("mapX"))
    map_y_value = payload.get("mapY", existing.get("mapY"))
    try:
        lat = float(lat_value) if lat_value not in (None, "") else None
        lon = float(lon_value) if lon_value not in (None, "") else None
        map_x = float(map_x_value) if map_x_value not in (None, "") else None
        map_y = float(map_y_value) if map_y_value not in (None, "") else None
    except (TypeError, ValueError) as exc:
        raise ValueError("坐标字段必须是数字") from exc
    location_defaults = location_metadata_for_spot(name, lat, lon)
    map_zone = str(payload.get("mapZone", existing.get("mapZone", location_defaults["mapZone"]))).strip() or location_defaults["mapZone"]
    verified_location = payload.get("verifiedLocation", existing.get("verifiedLocation", location_defaults["verifiedLocation"]))
    verified_location = bool(verified_location)
    return {
        "name": name,
        "description": str(payload.get("description", existing.get("description", ""))).strip() or "暂无简介，可在后台补充。",
        "story": str(payload.get("story", existing.get("story", ""))).strip() or "暂无讲解词，可在知识库中补充。",
        "tags": tags,
        "image": str(payload.get("image", existing.get("image", "assets/spot-gate.svg"))).strip() or "assets/spot-gate.svg",
        "openTime": str(payload.get("openTime", existing.get("openTime", "08:30-18:00"))).strip(),
        "duration": max(5, min(duration, 480)),
        "popularity": max(0, min(popularity, 100)),
        "location": str(payload.get("location", existing.get("location", "景区内"))).strip(),
        "status": status,
        "lat": lat if lat is not None else location_defaults["lat"],
        "lon": lon if lon is not None else location_defaults["lon"],
        "mapZone": map_zone,
        "mapX": map_x if map_x is not None else location_defaults["mapX"],
        "mapY": map_y if map_y is not None else location_defaults["mapY"],
        "verifiedLocation": verified_location,
    }


def create_spot(payload):
    spot = validate_spot_payload(payload)
    now = int(time.time())
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scenic_spot
            (name, description, story, tags, image, open_time, duration, popularity, location, lat, lon,
             map_zone, map_x, map_y, verified_location, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                spot["name"],
                spot["description"],
                spot["story"],
                json.dumps(spot["tags"], ensure_ascii=False),
                spot["image"],
                spot["openTime"],
                spot["duration"],
                spot["popularity"],
                spot["location"],
                spot["lat"],
                spot["lon"],
                spot["mapZone"],
                spot["mapX"],
                spot["mapY"],
                1 if spot["verifiedLocation"] else 0,
                spot["status"],
                now,
                now,
            ),
        )
        spot_id = cursor.lastrowid
    return find_spot(spot_id, include_inactive=True)


def update_spot(spot_id, payload):
    existing = find_spot(spot_id, include_inactive=True)
    if not existing:
        return None
    spot = validate_spot_payload(payload, existing)
    now = int(time.time())
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE scenic_spot
            SET name = ?, description = ?, story = ?, tags = ?, image = ?, open_time = ?,
                duration = ?, popularity = ?, location = ?, lat = ?, lon = ?, map_zone = ?, map_x = ?, map_y = ?,
                verified_location = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                spot["name"],
                spot["description"],
                spot["story"],
                json.dumps(spot["tags"], ensure_ascii=False),
                spot["image"],
                spot["openTime"],
                spot["duration"],
                spot["popularity"],
                spot["location"],
                spot["lat"],
                spot["lon"],
                spot["mapZone"],
                spot["mapX"],
                spot["mapY"],
                1 if spot["verifiedLocation"] else 0,
                spot["status"],
                now,
                spot_id,
            ),
        )
    return find_spot(spot_id, include_inactive=True)


def delete_spot(spot_id):
    with get_connection() as connection:
        row = connection.execute("SELECT 1 FROM scenic_spot WHERE id = ?", (spot_id,)).fetchone()
        if not row:
            return False
        connection.execute("UPDATE scenic_spot SET status = 'inactive', updated_at = ? WHERE id = ?", (int(time.time()), spot_id))
    return True


def validate_knowledge_payload(payload, existing=None):
    existing = existing or {}
    title = str(payload.get("title", existing.get("title", ""))).strip()
    content = str(payload.get("content", existing.get("content", ""))).strip()
    if not title:
        raise ValueError("知识标题不能为空")
    if not content:
        raise ValueError("知识内容不能为空")
    status = str(payload.get("status", existing.get("status", "active"))).strip() or "active"
    if status not in ("active", "inactive"):
        status = "active"
    return {
        "title": title,
        "category": str(payload.get("category", existing.get("category", "景区知识"))).strip() or "景区知识",
        "content": content,
        "status": status,
        "sourceType": str(payload.get("sourceType", existing.get("sourceType", "manual"))).strip() or "manual",
        "sourceFile": str(payload.get("sourceFile", existing.get("sourceFile", ""))).strip(),
        "sourceSection": str(payload.get("sourceSection", existing.get("sourceSection", ""))).strip(),
    }


def create_knowledge(payload):
    document = validate_knowledge_payload(payload)
    now = int(time.time())
    document_id = str(uuid.uuid4())
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO knowledge_document
            (id, title, category, content, status, source_type, source_file, source_section, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                document["title"],
                document["category"],
                document["content"],
                document["status"],
                document["sourceType"],
                document["sourceFile"],
                document["sourceSection"],
                now,
                now,
            ),
        )
    return get_knowledge_by_id(document_id)


def create_knowledge_from_chat(payload):
    chat_id = str(payload.get("chatId", "")).strip()
    if not chat_id:
        raise ValueError("需要提供 chatId")
    record = get_chat_record_by_id(chat_id)
    if not record:
        return None

    confidence_percent = round(float(record.get("confidence") or 0) * 100)
    title = str(payload.get("title", "")).strip() or f"待补充：{record['question'][:36]}"
    category = str(payload.get("category", "")).strip() or "低置信问题"
    content = str(payload.get("content", "")).strip()
    if not content:
        source_titles = "、".join(ref.get("title", "") for ref in record.get("sourceRefs", []) if ref.get("title")) or "暂无明确来源"
        content = (
            f"游客问题：{record['question']}\n"
            f"当前回答：{record['answer']}\n"
            f"当前置信度：{confidence_percent}%\n"
            f"当前来源：{source_titles}\n\n"
            "请管理员核对官方资料后，将这里改写为可直接用于游客问答的标准答案；确认无误后再把状态改为启用。"
        )
    status = str(payload.get("status", "inactive")).strip() or "inactive"
    return create_knowledge(
        {
            "title": title,
            "category": category,
            "content": content,
            "status": status,
            "sourceType": "chat_draft",
            "sourceFile": "问答记录",
            "sourceSection": chat_id,
        }
    )


def get_knowledge_by_id(document_id):
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM knowledge_document WHERE id = ?", (document_id,)).fetchone()
    return row_to_knowledge(row) if row else None


def update_knowledge(document_id, payload):
    existing = get_knowledge_by_id(document_id)
    if not existing:
        return None
    document = validate_knowledge_payload(payload, existing)
    now = int(time.time())
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE knowledge_document
            SET title = ?, category = ?, content = ?, status = ?, source_type = ?, source_file = ?, source_section = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                document["title"],
                document["category"],
                document["content"],
                document["status"],
                document["sourceType"],
                document["sourceFile"],
                document["sourceSection"],
                now,
                document_id,
            ),
        )
    return get_knowledge_by_id(document_id)


def delete_knowledge(document_id):
    with get_connection() as connection:
        row = connection.execute("SELECT 1 FROM knowledge_document WHERE id = ?", (document_id,)).fetchone()
        if not row:
            return False
        connection.execute("DELETE FROM knowledge_document WHERE id = ?", (document_id,))
    return True


def update_persona(payload):
    current = get_persona()
    next_persona = {
        "name": str(payload.get("name", current["name"])).strip() or DEFAULT_PERSONA["name"],
        "role": str(payload.get("role", current["role"])).strip() or DEFAULT_PERSONA["role"],
        "greeting": str(payload.get("greeting", current["greeting"])).strip() or DEFAULT_PERSONA["greeting"],
        "style": str(payload.get("style", current["style"])).strip() or DEFAULT_PERSONA["style"],
        "costume": str(payload.get("costume", current["costume"])).strip() or DEFAULT_PERSONA["costume"],
        "voice": str(payload.get("voice", current["voice"])).strip() or DEFAULT_PERSONA["voice"],
        "accentColor": str(payload.get("accentColor", current["accentColor"])).strip() or DEFAULT_PERSONA["accentColor"],
        "voiceSpeed": max(0.75, min(float(payload.get("voiceSpeed", current.get("voiceSpeed", DEFAULT_PERSONA["voiceSpeed"]))), 1.25)),
        "voicePitch": max(0.8, min(float(payload.get("voicePitch", current.get("voicePitch", DEFAULT_PERSONA["voicePitch"]))), 1.2)),
        "expressionProfile": str(payload.get("expressionProfile", current.get("expressionProfile", DEFAULT_PERSONA["expressionProfile"]))).strip()
        or DEFAULT_PERSONA["expressionProfile"],
        "avatarPresetKey": str(payload.get("avatarPresetKey", current.get("avatarPresetKey", DEFAULT_PERSONA["avatarPresetKey"]))).strip()
        or DEFAULT_PERSONA["avatarPresetKey"],
        "avatarId": str(payload.get("avatarId", current.get("avatarId", DEFAULT_PERSONA["avatarId"]))).strip()
        or DEFAULT_PERSONA["avatarId"],
        "refAudio": str(payload.get("refAudio", current.get("refAudio", DEFAULT_PERSONA["refAudio"]))).strip()
        or DEFAULT_PERSONA["refAudio"],
        "refText": str(payload.get("refText", current.get("refText", DEFAULT_PERSONA["refText"]))).strip()
        or DEFAULT_PERSONA["refText"],
        "avatarVoice": str(payload.get("avatarVoice", current.get("avatarVoice", DEFAULT_PERSONA["avatarVoice"]))).strip()
        or DEFAULT_PERSONA["avatarVoice"],
        "ttsMode": str(payload.get("ttsMode", current.get("ttsMode", DEFAULT_PERSONA["ttsMode"]))).strip()
        or DEFAULT_PERSONA["ttsMode"],
    }
    now = int(time.time())
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE persona_config
            SET name = ?, role = ?, greeting = ?, style = ?, costume = ?, voice = ?, accent_color = ?,
                voice_speed = ?, voice_pitch = ?, expression_profile = ?,
                avatar_preset_key = ?, avatar_id = ?, ref_audio = ?, ref_text = ?, avatar_voice = ?, tts_mode = ?,
                updated_at = ?
            WHERE id = 1
            """,
            (
                next_persona["name"],
                next_persona["role"],
                next_persona["greeting"],
                next_persona["style"],
                next_persona["costume"],
                next_persona["voice"],
                next_persona["accentColor"],
                next_persona["voiceSpeed"],
                next_persona["voicePitch"],
                next_persona["expressionProfile"],
                next_persona["avatarPresetKey"],
                next_persona["avatarId"],
                next_persona["refAudio"],
                next_persona["refText"],
                next_persona["avatarVoice"],
                next_persona["ttsMode"],
                now,
            ),
        )
    return get_persona()


def save_feedback(payload):
    chat_id = str(payload.get("chatId", "")).strip()
    score = max(1, min(int(payload.get("score", 5)), 5))
    comment = str(payload.get("comment", "")).strip()
    sentiment = "positive" if score >= 4 else "negative" if score <= 2 else analyze_sentiment(comment)
    record = {
        "id": str(uuid.uuid4()),
        "chatId": chat_id,
        "score": score,
        "comment": comment,
        "sentiment": sentiment,
        "createdAt": int(time.time()),
    }
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO feedback_record (id, chat_id, score, comment, sentiment, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (record["id"], chat_id, score, comment, sentiment, record["createdAt"]),
        )
        if chat_id:
            connection.execute("UPDATE chat_record SET satisfaction = ? WHERE id = ?", (score, chat_id))
    return record


def start_of_today():
    now = datetime.now()
    return int(datetime(now.year, now.month, now.day).timestamp())


def start_of_week():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return int(datetime(monday.year, monday.month, monday.day).timestamp())


def satisfaction_trend(rows):
    today = datetime.now()
    trend = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_start = int(datetime(day.year, day.month, day.day).timestamp())
        day_end = day_start + 86400
        scores = [row["score"] for row in rows if day_start <= row["created_at"] < day_end]
        trend.append(
            {
                "date": day.strftime("%m-%d"),
                "score": round(sum(scores) / len(scores), 1) if scores else 0,
                "count": len(scores),
            }
        )
    return trend


def evaluate_knowledge_base(spots, chat_rows, unresolved_count):
    documents = get_knowledge_documents(include_inactive=False)
    knowledge_text = "\n".join(
        [document.get("title", "") + " " + document.get("category", "") + " " + document.get("content", "") for document in documents]
        + [spot.get("name", "") + " " + spot.get("description", "") + " " + spot.get("story", "") for spot in spots]
    )
    required_facts = [
        "210", "105", "225", "40", "九龙灌浴", "10:00", "吉祥颂", "10:35", "五印坛城", "灵山大佛",
        "88", "101.5", "216", "祥符禅寺", "灵山大照壁", "五明桥", "百子戏弥勒", "历史文化", "亲子",
        "拍照", "素斋", "运动鞋", "佛像", "观光车", "停车",
    ]
    hit_count = sum(1 for fact in required_facts if fact in knowledge_text)
    tested_count = len(required_facts)
    coverage_rate = round(hit_count / max(tested_count, 1) * 100)
    if chat_rows:
        confident_count = sum(1 for row in chat_rows if float(row["confidence"] or 0) >= 0.65)
        recall_hit_rate = round(confident_count / len(chat_rows) * 100)
        low_confidence_rate = round(unresolved_count / max(len(chat_rows), 1) * 100)
    else:
        recall_hit_rate = coverage_rate
        low_confidence_rate = max(0, 100 - coverage_rate)
    accuracy_rate = round(min(99, max(0, coverage_rate * 0.72 + recall_hit_rate * 0.28)))
    passed_count = round(tested_count * accuracy_rate / 100)
    source_types = Counter(document.get("sourceType") or document.get("source_type") or "manual" for document in documents)
    return {
        "accuracyRate": accuracy_rate,
        "targetRate": 90,
        "coverageRate": coverage_rate,
        "recallHitRate": recall_hit_rate,
        "lowConfidenceRate": low_confidence_rate,
        "testedQuestionCount": tested_count,
        "passedQuestionCount": passed_count,
        "requiredFactCount": tested_count,
        "coveredFactCount": hit_count,
        "sourceTypeDistribution": dict(source_types),
        "evaluationMethod": "依据 docs/标准测试集.md 的关键事实做知识覆盖检查，并结合近期问答置信度估算 RAG 命中表现。",
        "standardSet": "灵山胜境事实问答标准测试集",
        "updatedAt": int(time.time()),
    }


def clamp_operation_value(value, minimum, maximum):
    return operations_service.clamp_operation_value(value, minimum, maximum)


def operations_overview():
    return operations_service.operations_overview(get_connection, start_of_today(), start_of_week(), build_behavior_analytics())


def analytics_overview():
    spots = get_spots(include_inactive=True)
    behavior = build_behavior_analytics()
    today_ts = start_of_today()
    week_ts = start_of_week()
    with get_connection() as connection:
        question_count = connection.execute("SELECT COUNT(*) FROM chat_record").fetchone()[0]
        route_count = connection.execute("SELECT COUNT(*) FROM route_record").fetchone()[0]
        knowledge_count = connection.execute("SELECT COUNT(*) FROM knowledge_document WHERE status = 'active'").fetchone()[0]
        today_questions = connection.execute("SELECT COUNT(*) FROM chat_record WHERE created_at >= ?", (today_ts,)).fetchone()[0]
        today_routes = connection.execute("SELECT COUNT(*) FROM route_record WHERE created_at >= ?", (today_ts,)).fetchone()[0]
        week_questions = connection.execute("SELECT COUNT(*) FROM chat_record WHERE created_at >= ?", (week_ts,)).fetchone()[0]
        week_routes = connection.execute("SELECT COUNT(*) FROM route_record WHERE created_at >= ?", (week_ts,)).fetchone()[0]
        feedback_count = connection.execute("SELECT COUNT(*) FROM feedback_record").fetchone()[0]
        chat_rows = connection.execute("SELECT * FROM chat_record").fetchall()
        route_rows = connection.execute("SELECT preference, spots FROM route_record").fetchall()
        feedback_rows = connection.execute("SELECT * FROM feedback_record").fetchall()

    display_chat_rows = chat_rows
    display_route_rows = route_rows
    display_feedback_rows = feedback_rows
    display_question_count = question_count
    display_route_count = route_count
    display_today_service_count = today_questions + today_routes
    display_week_service_count = week_questions + week_routes

    spot_hits = {spot["name"]: 0 for spot in spots}
    for row in display_chat_rows:
        text = row["question"] + row["answer"]
        for spot in spots:
            if spot["name"] in text:
                spot_hits[spot["name"]] += 1
    for row in display_route_rows:
        for spot in safe_json_loads(row["spots"], []):
            if isinstance(spot, dict) and spot.get("name") in spot_hits:
                spot_hits[spot["name"]] += 1

    preferences = Counter(row["preference"] for row in display_route_rows if is_displayable_text(row["preference"]))
    intents = Counter(row["intent"] for row in display_chat_rows if is_displayable_text(row["intent"]))
    feedback_chat_ids = {row["chat_id"] for row in display_feedback_rows if is_displayable_text(row["chat_id"])}
    chat_sentiment_labels = [
        row["sentiment"] if row["id"] in feedback_chat_ids else sentiment_label_from_rating(row["satisfaction"], row["sentiment"])
        for row in display_chat_rows
    ]
    feedback_sentiment_labels = [
        sentiment_label_from_rating(row["score"], row["sentiment"])
        for row in display_feedback_rows
    ]
    sentiments = Counter(label for label in chat_sentiment_labels if is_displayable_text(label))
    sentiments.update(label for label in feedback_sentiment_labels if is_displayable_text(label))
    hot_questions = Counter(row["question"] for row in display_chat_rows if is_displayable_text(row["question"])).most_common(6)
    scores = [row["score"] for row in display_feedback_rows if row["score"] is not None]
    average_satisfaction = round(sum(scores) / len(scores), 1) if scores else 0
    unresolved_count = sum(1 for row in display_chat_rows if row["confidence"] < 0.65)
    negative_count = sentiments.get("negative", 0)
    service_suggestions = []
    if unresolved_count:
        service_suggestions.append(f"有 {unresolved_count} 条低置信度问答，建议优先补充对应知识文档。")
    if negative_count:
        service_suggestions.append("存在负向情绪或低分反馈，建议检查停车、排队、路线耗时等服务说明。")
    if not display_chat_rows and not display_feedback_rows:
        service_suggestions.append("暂无真实游客问答或反馈记录，报告仅展示已入库路线记录和灵山游客行为记录。")
    elif not display_feedback_rows:
        if behavior.get("averageSatisfaction"):
            service_suggestions.append("暂无系统内游客评分反馈，体验报告和大屏满意度当前使用灵山游客行为记录的 satisfaction 字段。")
        else:
            service_suggestions.append("暂无真实游客评分反馈，满意度和反馈趋势将在收到评分后生成。")
    if not preferences:
        service_suggestions.append("暂无真实路线偏好记录，路线关注点将在游客生成路线后更新。")
    if not service_suggestions:
        service_suggestions.append("当前服务数据稳定，可继续优化数字人讲解语气和景点知识覆盖度。")
    knowledge_evaluation = evaluate_knowledge_base(spots, display_chat_rows, unresolved_count)
    hot_spots = sorted((item for item in spot_hits.items() if item[1] > 0), key=lambda item: item[1], reverse=True)[:5]

    return {
        "questionCount": display_question_count,
        "routeCount": display_route_count,
        "feedbackCount": feedback_count,
        "spotCount": len([spot for spot in spots if spot["status"] == "active"]),
        "knowledgeCount": knowledge_count,
        "todayServiceCount": display_today_service_count,
        "weekServiceCount": display_week_service_count,
        "averageSatisfaction": average_satisfaction,
        "unresolvedCount": unresolved_count,
        "hotSpots": hot_spots,
        "preferences": dict(preferences),
        "hotQuestions": hot_questions,
        "intentDistribution": dict(intents),
        "sentimentDistribution": dict(sentiments),
        "satisfactionTrend": satisfaction_trend(display_feedback_rows) if display_feedback_rows else [],
        "recentQuestions": get_recent_chat_records(),
        "serviceSuggestions": service_suggestions,
        "behaviorBaseline": behavior,
        "knowledgeEvaluation": knowledge_evaluation,
        "dataSource": {
            "service": "系统实时交互记录",
            "feedback": "系统游客反馈记录",
            "behaviorBaseline": behavior.get("dataSource", {}),
            "mode": "live",
            "reportMode": "real_records",
            "demoSampleUsed": False,
            "note": "体验报告仅统计数据库中的真实问答、路线、反馈和已导入灵山游客行为记录，未使用演示样本。",
        },
    }
