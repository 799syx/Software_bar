import base64
import binascii
import re
import time
from urllib.parse import parse_qs, urlparse

import app_core as core
import location_service
import static_server


class Route:
    def __init__(self, matcher, pattern, handler):
        self.matcher = matcher
        self.pattern = pattern
        self.handler = handler
        self._compiled = re.compile(pattern) if matcher == "regex" else None

    def match(self, path):
        if self.matcher == "exact":
            return () if path == self.pattern else None
        if self.matcher == "prefix":
            return () if path == self.pattern or path.startswith(f"{self.pattern}/") else None
        if self.matcher == "regex":
            matched = self._compiled.match(path)
            return matched.groups() if matched else None
        return None


def exact(path, handler):
    return Route("exact", path, handler)


def prefix(path, handler):
    return Route("prefix", path, handler)


def regex(pattern, handler):
    return Route("regex", pattern, handler)


def parse_int_id(path):
    try:
        return int(path.rsplit("/", 1)[-1])
    except ValueError:
        return None


def get_spots(handler, _parsed):
    core.json_response(handler, {"items": core.get_spots()})


def get_nearby_spots(handler, parsed):
    params = parse_qs(parsed.query)
    try:
        lat = float(params["lat"][0])
        lon = float(params["lon"][0])
        if not location_service.is_finite_number(lat) or not location_service.is_finite_number(lon):
            raise ValueError("coordinates must be finite")
    except (KeyError, ValueError, IndexError):
        core.error_response(handler, "lat and lon are required", 400, "missing_coordinates")
        return
    try:
        limit = int(params.get("limit", ["5"])[0])
    except (TypeError, ValueError):
        limit = 5
    accuracy = core.parse_optional_float(params.get("accuracy", [None])[0])
    core.json_response(handler, core.nearby_location_result(lat, lon, limit, accuracy))


def get_location_anchors(handler, _parsed):
    core.json_response(handler, {"items": core.location_anchors()})


def get_location_resolve(handler, parsed):
    params = parse_qs(parsed.query)
    core.json_response(handler, core.resolve_location_code(params.get("code", [""])[0]))


def get_spot_detail(handler, _parsed):
    spot_id = parse_int_id(urlparse(handler.path).path)
    if spot_id is None:
        core.error_response(handler, "invalid spot id", 400, "invalid_spot_id")
        return
    spot = core.find_spot(spot_id)
    if not spot:
        core.error_response(handler, "spot not found", 404, "spot_not_found")
        return
    core.json_response(handler, spot)


def get_persona(handler, _parsed):
    core.json_response(handler, core.get_persona())


def get_llm_status(handler, _parsed):
    core.json_response(handler, core.llm_status())


def get_tts_status(handler, _parsed):
    core.json_response(handler, core.tts_status())


def get_asr_status(handler, _parsed):
    core.json_response(handler, core.asr_status())


def get_system_capabilities(handler, _parsed):
    core.json_response(handler, core.system_capabilities())


def get_chat_suggestions(handler, _parsed):
    core.json_response(
        handler,
        {
            "items": [
                "景区几点开放？",
                "适合亲子游的景点有哪些？",
                "哪里适合拍照打卡？",
                "停车场在哪里？",
                "灵山大佛有什么特色？",
                "九龙灌浴什么时候表演？",
                "梵宫吉祥颂演出时间？",
                "如果我喜欢历史文化，应该怎么逛？",
            ]
        },
    )


def get_route_options(handler, _parsed):
    core.json_response(
        handler,
        {
            "durations": [60, 120, 180, 240, 300, 360],
            "preferences": ["佛教文化", "历史文化", "亲子游", "拍照打卡", "自然风光", "演艺体验", "餐饮购物", "轻松休闲"],
        },
    )


def get_admin_spots(handler, _parsed):
    core.json_response(handler, {"items": core.get_spots(include_inactive=True)})


def get_admin_knowledge(handler, _parsed):
    core.json_response(handler, {"items": core.get_knowledge_documents(include_inactive=True)})


def get_admin_chat_records(handler, parsed):
    params = parse_qs(parsed.query)
    limit = int(params.get("limit", ["20"])[0])
    low_confidence = params.get("lowConfidence", ["0"])[0].lower() in {"1", "true", "yes"}
    core.json_response(handler, {"items": core.get_recent_chat_records(max(1, min(limit, 100)), low_confidence=low_confidence)})


def get_operations_overview(handler, _parsed):
    core.json_response(handler, core.operations_overview())


def get_analytics_overview(handler, _parsed):
    core.json_response(handler, core.analytics_overview())


def get_behavior_analytics(handler, _parsed):
    core.json_response(handler, core.build_behavior_analytics())


def get_mobile_static(handler, parsed):
    static_server.serve_mobile_static(handler, parsed.path)


def get_public_asset(handler, parsed):
    static_server.serve_public_asset(handler, parsed.path)


def post_chat(handler, parsed):
    payload = core.read_json(handler)
    question = str(payload.get("question", "")).strip()
    if not question:
        core.error_response(handler, "question cannot be empty", 400, "empty_question")
        return
    if len(question) > 500:
        core.error_response(handler, "question is too long", 400, "question_too_long")
        return

    started_at = time.perf_counter()
    answer = core.answer_question(question)
    latency_ms = int((time.perf_counter() - started_at) * 1000)
    record = core.build_chat_record(question, answer, latency_ms)
    core.save_chat_record(record)
    if parsed.path == "/api/chat/stream":
        core.stream_chat_record(handler, record)
        return
    core.json_response(handler, record)


def post_route_recommend(handler, _parsed):
    payload = core.read_json(handler)
    duration = max(30, min(int(payload.get("duration", 180)), 480))
    preference = str(payload.get("preference", "佛教文化"))
    core.json_response(handler, core.recommend_route(duration, preference))


def post_vision_analyze(handler, _parsed):
    payload = core.read_json(handler)
    started_at = time.perf_counter()
    result = core.analyze_scenic_image(payload)
    result["latencyMs"] = int((time.perf_counter() - started_at) * 1000)
    core.json_response(handler, result)


def post_tts_synthesize(handler, _parsed):
    payload = core.read_json(handler)
    try:
        core.json_response(handler, core.synthesize_with_doubao(payload))
    except RuntimeError as exc:
        core.json_response(handler, {"available": False, "fallback": True, "provider": "doubao", "message": str(exc)}, 200)


def post_asr_transcribe(handler, _parsed):
    payload = core.read_json(handler)
    try:
        core.json_response(handler, core.transcribe_audio(payload))
    except RuntimeError as exc:
        core.json_response(
            handler,
            {"available": False, "fallback": True, "provider": core.asr_config()["provider"], "message": str(exc), "text": ""},
            200,
        )


def post_public_data_reimport(handler, _parsed):
    payload = core.read_json(handler)
    core.json_response(handler, core.reimport_public_data(bool(payload.get("importBehaviorRows"))))


def post_behavior_upload_xlsx(handler, _parsed):
    payload = core.read_json(handler)
    file_name = re.sub(r"[\\/:*?\"<>|]+", "_", str(payload.get("fileName") or "behavior.xlsx")).strip() or "behavior.xlsx"
    if not file_name.lower().endswith(".xlsx"):
        raise ValueError("only .xlsx files are supported")
    try:
        content = decode_data_url(payload.get("dataUrl"))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid xlsx dataUrl") from exc
    core.json_response(handler, core.import_behavior_excel_upload(file_name, content))


def post_admin_spot(handler, _parsed):
    core.json_response(handler, core.create_spot(core.read_json(handler)), 201)


def decode_data_url(data_url):
    text = str(data_url or "")
    if "," not in text:
        raise ValueError("dataUrl is required")
    return base64.b64decode(text.split(",", 1)[1], validate=True)


def post_knowledge_upload_docx(handler, _parsed):
    payload = core.read_json(handler)
    file_name = re.sub(r"[\\/:*?\"<>|]+", "_", str(payload.get("fileName") or "uploaded.docx")).strip() or "uploaded.docx"
    if not file_name.lower().endswith(".docx"):
        raise ValueError("only .docx files are supported")
    try:
        content = decode_data_url(payload.get("dataUrl"))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid docx dataUrl") from exc
    if len(content) > core.MAX_JSON_BODY_BYTES:
        raise ValueError("docx file is too large")

    upload_dir = core.DATA_DIR / "tmp" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = upload_dir / f"{core.uuid.uuid4().hex}-{file_name}"
    try:
        tmp_path.write_bytes(content)
        paragraphs = core.read_docx_paragraphs(tmp_path)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    chunks = core.chunk_paragraphs(paragraphs, max_chars=2200)
    if not chunks:
        raise ValueError("docx file has no readable paragraphs")

    stem = re.sub(r"\.docx$", "", file_name, flags=re.I)
    items = []
    for index, chunk in enumerate(chunks, start=1):
        title = stem if len(chunks) == 1 else f"{stem} {index:02d}"
        items.append(
            core.create_knowledge(
                {
                    "title": title,
                    "category": "上传资料",
                    "content": chunk,
                    "status": "active",
                    "sourceType": "manual",
                    "sourceFile": file_name,
                    "sourceSection": f"docx-paragraphs-{index}",
                }
            )
        )

    core.json_response(
        handler,
        {"items": items, "imported": len(items), "paragraphCount": len(paragraphs), "sourceFile": file_name, "mode": "paragraph_chunks"},
        201,
    )


def post_knowledge_from_chat(handler, _parsed):
    document = core.create_knowledge_from_chat(core.read_json(handler))
    if not document:
        core.error_response(handler, "chat record not found", 404, "chat_record_not_found")
        return
    core.json_response(handler, document, 201)


def post_admin_knowledge(handler, _parsed):
    core.json_response(handler, core.create_knowledge(core.read_json(handler)), 201)


def post_feedback(handler, _parsed):
    core.json_response(handler, core.save_feedback(core.read_json(handler)), 201)


def put_admin_spot(handler, _parsed):
    spot_id = parse_int_id(urlparse(handler.path).path)
    if spot_id is None:
        core.error_response(handler, "invalid spot id", 400, "invalid_spot_id")
        return
    spot = core.update_spot(spot_id, core.read_json(handler))
    if not spot:
        core.error_response(handler, "spot not found", 404, "spot_not_found")
        return
    core.json_response(handler, spot)


def put_admin_knowledge(handler, _parsed):
    document_id = urlparse(handler.path).path.rsplit("/", 1)[-1]
    document = core.update_knowledge(document_id, core.read_json(handler))
    if not document:
        core.error_response(handler, "knowledge document not found", 404, "knowledge_not_found")
        return
    core.json_response(handler, document)


def put_admin_persona(handler, _parsed):
    core.json_response(handler, core.update_persona(core.read_json(handler)))


def delete_admin_spot(handler, _parsed):
    spot_id = parse_int_id(urlparse(handler.path).path)
    if spot_id is None:
        core.error_response(handler, "invalid spot id", 400, "invalid_spot_id")
        return
    if not core.delete_spot(spot_id):
        core.error_response(handler, "spot not found", 404, "spot_not_found")
        return
    core.json_response(handler, {"ok": True})


def delete_admin_knowledge(handler, _parsed):
    document_id = urlparse(handler.path).path.rsplit("/", 1)[-1]
    if not core.delete_knowledge(document_id):
        core.error_response(handler, "knowledge document not found", 404, "knowledge_not_found")
        return
    core.json_response(handler, {"ok": True})


ROUTES = {
    "GET": [
        exact("/api/spots", get_spots),
        exact("/api/spots/nearby", get_nearby_spots),
        exact("/api/location/anchors", get_location_anchors),
        exact("/api/location/resolve", get_location_resolve),
        regex(r"^/api/spots/[^/]+$", get_spot_detail),
        exact("/api/persona", get_persona),
        exact("/api/llm/status", get_llm_status),
        exact("/api/tts/status", get_tts_status),
        exact("/api/asr/status", get_asr_status),
        exact("/api/system/capabilities", get_system_capabilities),
        exact("/api/chat/suggestions", get_chat_suggestions),
        exact("/api/routes/options", get_route_options),
        exact("/api/analytics/overview", get_analytics_overview),
        exact("/api/admin/spots", get_admin_spots),
        exact("/api/admin/knowledge", get_admin_knowledge),
        exact("/api/admin/chat-records", get_admin_chat_records),
        exact("/api/admin/operations/overview", get_operations_overview),
        exact("/api/admin/analytics/overview", get_analytics_overview),
        exact("/api/admin/analytics/behavior", get_behavior_analytics),
        prefix("/mobile", get_mobile_static),
        prefix("/assets", get_public_asset),
    ],
    "POST": [
        exact("/api/chat", post_chat),
        exact("/api/chat/stream", post_chat),
        exact("/api/routes/recommend", post_route_recommend),
        exact("/api/vision/analyze", post_vision_analyze),
        exact("/api/tts/synthesize", post_tts_synthesize),
        exact("/api/asr/transcribe", post_asr_transcribe),
        exact("/api/admin/public-data/reimport", post_public_data_reimport),
        exact("/api/admin/behavior/upload-xlsx", post_behavior_upload_xlsx),
        exact("/api/admin/spots", post_admin_spot),
        exact("/api/admin/knowledge/upload-docx", post_knowledge_upload_docx),
        exact("/api/admin/knowledge/from-chat", post_knowledge_from_chat),
        exact("/api/admin/knowledge", post_admin_knowledge),
        exact("/api/feedback", post_feedback),
    ],
    "PUT": [
        regex(r"^/api/admin/spots/[^/]+$", put_admin_spot),
        regex(r"^/api/admin/knowledge/[^/]+$", put_admin_knowledge),
        exact("/api/admin/persona", put_admin_persona),
    ],
    "DELETE": [
        regex(r"^/api/admin/spots/[^/]+$", delete_admin_spot),
        regex(r"^/api/admin/knowledge/[^/]+$", delete_admin_knowledge),
    ],
}


def dispatch(method, handler):
    parsed = urlparse(handler.path)
    path = parsed.path
    for route in ROUTES.get(method, []):
        match = route.match(path)
        if match is not None:
            route.handler(handler, parsed, *match)
            return

    if method == "GET":
        static_server.serve_static(handler, path)
        return

    core.error_response(handler, "not found", 404, "not_found")
