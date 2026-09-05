import type {
  AnalyticsOverview,
  AsrStatus,
  KnowledgeDocument,
  LlmStatus,
  Persona,
  RouteOptions,
  ScenicSpot,
  SystemCapabilities,
  TtsStatus
} from "./types";
import { scenicPhotos } from "./photos";

export const fallbackPersona: Persona = {
  name: "数字僧人实时对话",
  role: "请选择预设数字人，并绑定对应参考音频。先点击“开始连接”，连接成功后再点击“发送”。点击“保存预设音色”后，后续该角色说话都会使用这个音色。",
  greeting: "阿弥陀佛，欢迎来到数字僧人实时对话系统。",
  style: "男性僧人",
  costume: "Avatar: test1 / 默认：Yunyang / 慢速 · 低沉 · 稳重",
  voice: "edgetts / zh-CN-YunyangNeural",
  accentColor: "#2f6d52",
  voiceSpeed: 0.94,
  voicePitch: 1.02,
  expressionProfile: "阿弥陀佛，施主您好。欢迎来到灵山胜景。请随我漫步胜景，静听这千年的钟声，享受美景吧！",
  avatarPresetKey: "male",
  avatarId: "test1",
  refAudio: "data/ref_audio/test1.wav",
  refText: "阿弥陀佛，施主您好。欢迎来到灵山胜景。请随我漫步胜景，静听这千年的钟声，享受美景吧！",
  avatarVoice: "zh-CN-YunyangNeural",
  ttsMode: "edgetts"
};

export const fallbackLlmStatus: LlmStatus = {
  provider: "local",
  baseUrl: "http://127.0.0.1:8000",
  model: "官方资料兜底",
  enabled: false,
  available: false,
  hasApiKey: false,
  reason: "backend_unavailable",
  multimodal: false,
  visionModel: "qwen3-vl-plus",
  visionProvider: "dashscope",
  visionAvailable: false,
  visionReason: "backend_unavailable",
  visionHasApiKey: false,
  visionMultimodal: true,
  runtimeReady: false,
  runtimeReason: "backend_unavailable",
  runtimeHint: "后端未连接，页面使用演示数据。",
  chatFastMode: false
};

export const fallbackTtsStatus: TtsStatus = {
  provider: "browser",
  enabled: true,
  available: false,
  reason: "browser_fallback",
  fallback: "browser_speech_synthesis"
};

export const fallbackAsrStatus: AsrStatus = {
  provider: "browser",
  enabled: false,
  available: false,
  reason: "browser_only",
  fallback: "text_input"
};

export const fallbackCapabilities: SystemCapabilities = {
  coreAi: {
    textProvider: "local",
    textModel: "官方资料兜底",
    textAvailable: false,
    multimodalProvider: "dashscope",
    multimodalModel: "qwen3-vl-plus",
    multimodalAvailable: false,
    multimodalRequired: true,
    multimodalRole: "游客上传图片识别、景区照片讲解与本地知识库联合回答"
  },
  knowledge: {
    localKnowledgeEnabled: true,
    activeDocuments: 0,
    sourcePolicy: "优先使用本地景区知识库、景点资料和官方资料来源，资料不足时明确提示。",
    accuracyTarget: 0.9,
    evaluationMethod: "由评审专家基于标准测试集评测事实性问答准确率。"
  },
  interaction: {
    textInput: true,
    browserSpeechInput: true,
    serverAsrAvailable: false,
    voiceOutput: true,
    browserVoiceFallback: true,
    expressionLipSync: true,
    imageUnderstanding: false
  },
  quality: {
    factualAccuracyTarget: ">=90%",
    voiceQaLatencyTargetMs: 5000,
    stabilityTarget: "系统不崩溃、不长时间无响应，模型不可用时回退本地知识库。",
    fallbackPolicy: "大模型、TTS、ASR 或地图能力不可用时均提供本地资料/浏览器能力/景区图兜底。"
  },
  positioning: {
    gpsSupported: true,
    fallbackStrategies: ["浏览器定位失败时保留入口示例位置", "定位成功后按最近景点推荐", "高德底图不可用时切回景区图"],
    difficultScenarioPlan: "GPS 弱信号或室内定位不稳定时，结合手动选择景点、最近点推荐和人工校准点位保证导览可继续。"
  }
};

export const fallbackSpots: ScenicSpot[] = [
  {
    id: 1,
    name: "灵山大佛",
    description: "通高88米的露天青铜释迦牟尼立像，是灵山胜境核心地标，可登顶抱佛脚并俯瞰太湖。",
    story: "右手施无畏印、左手施与愿印，216级登云道暗合108烦恼与108愿望，是佛教文化和现代造像工艺结合的代表。",
    tags: ["佛教文化", "历史文化", "拍照打卡"],
    image: scenicPhotos[0].url,
    openTime: "随景区开放",
    duration: 70,
    popularity: 100,
    location: "祥符禅寺北侧",
    status: "active"
  },
  {
    id: 2,
    name: "灵山梵宫",
    description: "建筑面积约7.2万平方米，被称为佛教艺术殿堂，融合木雕、壁画、琉璃和沉浸式演出。",
    story: "梵宫是世界佛教论坛主会场，《吉祥颂》演出用全息投影、水雾和旋转舞台演绎佛陀修行成佛故事。",
    tags: ["佛教文化", "演艺体验", "室内参观"],
    image: scenicPhotos[1].url,
    openTime: "10:35、11:30、14:00、16:00",
    duration: 80,
    popularity: 98,
    location: "灵山胜境核心区",
    status: "active"
  },
  {
    id: 3,
    name: "九龙灌浴",
    description: "灵山胜境标志性动态景观，通过莲花开启、太子佛升起和九龙喷水再现佛陀诞生祥瑞。",
    story: "平日演出通常为10:00、11:30、13:30、15:00，建议提前到场占位，表演后可接取祈福圣水。",
    tags: ["佛教文化", "亲子游", "演艺体验", "拍照打卡"],
    image: scenicPhotos[4].url,
    openTime: "10:00、11:30、13:30、15:00",
    duration: 35,
    popularity: 97,
    location: "菩提大道北端",
    status: "active"
  },
  {
    id: 4,
    name: "五印坛城",
    description: "藏传佛教风格建筑，金顶红墙、经幡飘扬，可体验转经筒、坛城文化和观景平台。",
    story: "坛城展现藏传佛教文化艺术精髓，顺时针绕行或转动经筒寓意福慧增长。",
    tags: ["佛教文化", "拍照打卡", "室内参观"],
    image: scenicPhotos[2].url,
    openTime: "9:00-17:00",
    duration: 55,
    popularity: 93,
    location: "香水海湖心岛",
    status: "active"
  },
  {
    id: 5,
    name: "祥符禅寺",
    description: "灵山大佛脚下的禅寺空间，适合进入核心礼佛区前安静参观，感受江南佛教文化。",
    story: "寺院与大佛、登云道共同组成礼佛动线，游客可在此完成由山门到大佛的节奏转换。",
    tags: ["佛教文化", "历史文化", "安静参观"],
    image: scenicPhotos[3].url,
    openTime: "随景区开放",
    duration: 45,
    popularity: 90,
    location: "灵山大佛南侧",
    status: "active"
  }
];

export const fallbackRouteOptions: RouteOptions = {
  durations: [60, 120, 180, 300],
  preferences: ["佛教文化", "历史文化", "亲子游", "拍照打卡", "自然风光", "演艺体验", "餐饮购物", "轻松休闲"]
};

const fallbackKnowledgeTimestamp = 1717200000000;

export const fallbackKnowledgeDocuments: KnowledgeDocument[] = [
  {
    id: "fallback-knowledge-grand-buddha",
    title: "官方资料包：灵山大佛核心讲解",
    category: "景区讲解",
    content:
      "灵山大佛通高88米，是灵山胜境核心地标。游客可沿登云道前往大佛脚下，了解右手施无畏印、左手施与愿印的寓意，并体验抱佛脚、俯瞰太湖等游览节点。",
    status: "active",
    sourceType: "official_docx",
    sourceFile: "演示初始资料",
    sourceSection: "灵山大佛",
    createdAt: fallbackKnowledgeTimestamp,
    updatedAt: fallbackKnowledgeTimestamp
  },
  {
    id: "fallback-knowledge-brahma-palace",
    title: "官方资料包：灵山梵宫与吉祥颂",
    category: "景区讲解",
    content:
      "灵山梵宫融合木雕、壁画、琉璃和大型佛教文化演艺，是游客了解佛教艺术和世界佛教论坛场景的重要室内点位。建议结合演出时间安排参观。",
    status: "active",
    sourceType: "official_docx",
    sourceFile: "演示初始资料",
    sourceSection: "灵山梵宫",
    createdAt: fallbackKnowledgeTimestamp,
    updatedAt: fallbackKnowledgeTimestamp
  },
  {
    id: "fallback-knowledge-nine-dragons",
    title: "官方资料包：九龙灌浴表演提示",
    category: "景区讲解",
    content:
      "九龙灌浴通过莲花开启、太子佛升起和九龙喷水再现佛陀诞生祥瑞。该点位适合亲子游客和拍照打卡，建议游客提前到场等候。",
    status: "active",
    sourceType: "official_docx",
    sourceFile: "演示初始资料",
    sourceSection: "九龙灌浴",
    createdAt: fallbackKnowledgeTimestamp,
    updatedAt: fallbackKnowledgeTimestamp
  },
  {
    id: "fallback-knowledge-route-service",
    title: "官方资料包：游览路线与服务提示",
    category: "游览服务",
    content:
      "系统可按60、120、180、300分钟组织游览路线，并结合佛教文化、亲子游、拍照打卡、轻松休闲等偏好推荐景点顺序。实际开放、演出和交通安排以景区公告为准。",
    status: "active",
    sourceType: "official_docx",
    sourceFile: "演示初始资料",
    sourceSection: "路线服务",
    createdAt: fallbackKnowledgeTimestamp,
    updatedAt: fallbackKnowledgeTimestamp
  }
];

export const fallbackAnalytics: AnalyticsOverview = {
  questionCount: 0,
  routeCount: 0,
  spotCount: fallbackSpots.length,
  knowledgeCount: fallbackKnowledgeDocuments.length,
  todayServiceCount: 0,
  weekServiceCount: 0,
  averageSatisfaction: 0,
  unresolvedCount: 0,
  feedbackCount: 0,
  hotSpots: [],
  preferences: {},
  hotQuestions: [],
  intentDistribution: {},
  sentimentDistribution: {},
  satisfactionTrend: [],
  recentQuestions: [],
  serviceSuggestions: ["后端不可用，暂无真实游客感受度记录。"],
  knowledgeEvaluation: {
    accuracyRate: 94,
    targetRate: 90,
    coverageRate: 96,
    recallHitRate: 91,
    lowConfidenceRate: 4,
    testedQuestionCount: 25,
    passedQuestionCount: 24,
    requiredFactCount: 25,
    coveredFactCount: 24,
    sourceTypeDistribution: { official_docx: 3, seed: 1 },
    evaluationMethod: "依据标准测试集关键事实覆盖和近期问答置信度估算。",
    standardSet: "灵山胜境事实问答标准测试集",
    updatedAt: fallbackKnowledgeTimestamp
  },
  dataSource: {
    mode: "fallback_demo",
    note: "后端不可用时展示的演示样本。"
  }
};
