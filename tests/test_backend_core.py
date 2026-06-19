import base64
import io
import json
import os
import shutil
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import app  # noqa: E402
import search_engine  # noqa: E402
import streaming  # noqa: E402


class EnvPatch:
    def __init__(self, values):
        self.values = values
        self.original = {}

    def __enter__(self):
        for key, value in self.values.items():
            self.original[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        for key, value in self.original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class BackendCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.init_database()
        with app.get_connection() as connection:
            app.sync_behavior_visit_records(connection)

    def test_quote_table_name_rejects_unknown_table(self):
        with self.assertRaises(ValueError):
            app.quote_table_name("scenic_spot; drop table scenic_spot")

    def test_public_llm_config_hides_api_key(self):
        config = {
            "provider": "dashscope",
            "baseUrl": "https://example.com/v1",
            "model": "qwen3-vl-plus",
            "enabled": True,
            "available": True,
            "hasApiKey": True,
            "apiKey": "sk-secret",
            "reason": "ready",
            "multimodal": True,
        }
        public = app.public_llm_config(config)
        self.assertNotIn("apiKey", public)

    def test_admin_token_requires_explicit_env(self):
        with EnvPatch({"SCENIC_ADMIN_TOKEN": None}):
            self.assertEqual(app.admin_token(), "")
        with EnvPatch({"SCENIC_ADMIN_TOKEN": "unit-test-token"}):
            self.assertEqual(app.admin_token(), "unit-test-token")

    def test_vision_config_is_independent_from_deepseek_text_config(self):
        with EnvPatch(
            {
                "SCENIC_LLM_PROVIDER": "deepseek",
                "SCENIC_LLM_MODEL": "deepseek-v4-pro",
                "SCENIC_LLM_BASE_URL": "https://api.deepseek.com",
                "DEEPSEEK_API_KEY": "sk-deepseek",
                "SCENIC_VISION_PROVIDER": "dashscope",
                "SCENIC_VISION_MODEL": "qwen3-vl-flash",
                "SCENIC_VISION_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "SCENIC_VISION_API_KEY": "sk-vision",
                "DASHSCOPE_API_KEY": None,
            }
        ):
            text_config = app.get_llm_config()
            vision_config = app.get_vision_llm_config()

        self.assertEqual(text_config["provider"], "deepseek")
        self.assertEqual(text_config["baseUrl"], "https://api.deepseek.com")
        self.assertEqual(vision_config["provider"], "dashscope")
        self.assertEqual(vision_config["model"], "qwen3-vl-flash")
        self.assertEqual(vision_config["baseUrl"], "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.assertEqual(vision_config["apiKey"], "sk-vision")
        self.assertNotEqual(text_config["baseUrl"], vision_config["baseUrl"])

    def test_vision_config_defaults_to_dashscope_plus(self):
        with EnvPatch(
            {
                "SCENIC_VISION_PROVIDER": None,
                "SCENIC_VISION_MODEL": None,
                "SCENIC_VISION_BASE_URL": None,
                "SCENIC_VISION_API_KEY": None,
                "DASHSCOPE_API_KEY": None,
            }
        ):
            vision_config = app.get_vision_llm_config()

        self.assertEqual(vision_config["provider"], "dashscope")
        self.assertEqual(vision_config["model"], "qwen3-vl-plus")
        self.assertEqual(vision_config["baseUrl"], "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.assertTrue(vision_config["multimodal"])

    def test_analyze_scenic_image_uses_independent_vision_config(self):
        image_data = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii")
        seen_config = {}
        original = app.call_openai_compatible_llm

        def fake_llm(_messages, config=None):
            seen_config.update(config or {})
            return {"content": "这是一张景区照片讲解。", "model": config["model"], "provider": config["provider"]}

        app.call_openai_compatible_llm = fake_llm
        try:
            with EnvPatch(
                {
                    "SCENIC_LLM_PROVIDER": "deepseek",
                    "SCENIC_LLM_MODEL": "deepseek-v4-pro",
                    "SCENIC_LLM_BASE_URL": "https://api.deepseek.com",
                    "DEEPSEEK_API_KEY": "sk-deepseek",
                    "SCENIC_VISION_PROVIDER": "dashscope",
                    "SCENIC_VISION_MODEL": "qwen3-vl-flash",
                    "SCENIC_VISION_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "SCENIC_VISION_API_KEY": "sk-vision",
                    "DASHSCOPE_API_KEY": None,
                }
            ):
                result = app.analyze_scenic_image({"image": f"data:image/png;base64,{image_data}"})
        finally:
            app.call_openai_compatible_llm = original

        self.assertFalse(result["fallback"])
        self.assertEqual(seen_config["provider"], "dashscope")
        self.assertEqual(seen_config["model"], "qwen3-vl-flash")
        self.assertEqual(seen_config["apiKey"], "sk-vision")
        self.assertNotEqual(seen_config["baseUrl"], "https://api.deepseek.com")

    def test_normalize_image_data_url_accepts_small_png(self):
        data = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii")
        result = app.normalize_image_data_url(f"data:image/png;base64,{data}")
        self.assertTrue(result.startswith("data:image/png;base64,"))

    def test_normalize_image_data_url_rejects_svg(self):
        data = base64.b64encode(b"<svg></svg>").decode("ascii")
        with self.assertRaises(ValueError):
            app.normalize_image_data_url(f"data:image/svg+xml;base64,{data}")

    def test_classify_route_intent(self):
        self.assertEqual(app.classify_intent("如果我喜欢历史文化，应该怎么逛？"), "路线推荐")

    def test_answer_question_falls_back_when_llm_times_out(self):
        original = app.generate_with_llm
        original_fast_mode = os.environ.get("SCENIC_CHAT_FAST_MODE")
        os.environ["SCENIC_CHAT_FAST_MODE"] = "false"

        def fail_with_timeout(_messages):
            raise TimeoutError("simulated timeout")

        app.generate_with_llm = fail_with_timeout
        try:
            result = app.answer_question("景区几点开放？")
        finally:
            app.generate_with_llm = original
            if original_fast_mode is None:
                os.environ.pop("SCENIC_CHAT_FAST_MODE", None)
            else:
                os.environ["SCENIC_CHAT_FAST_MODE"] = original_fast_mode

        self.assertTrue(result["fallback"])
        self.assertIn("answer", result)

    def test_answer_question_fast_mode_skips_llm(self):
        original = app.generate_with_llm
        original_fast_mode = os.environ.get("SCENIC_CHAT_FAST_MODE")
        os.environ["SCENIC_CHAT_FAST_MODE"] = "true"

        def fail_if_called(_messages):
            raise AssertionError("LLM should not be called in fast mode")

        app.generate_with_llm = fail_if_called
        try:
            result = app.answer_question("景区几点开放？")
        finally:
            app.generate_with_llm = original
            if original_fast_mode is None:
                os.environ.pop("SCENIC_CHAT_FAST_MODE", None)
            else:
                os.environ["SCENIC_CHAT_FAST_MODE"] = original_fast_mode

        self.assertTrue(result["fallback"])
        self.assertIn("开放", result["answer"])

    def test_confident_knowledge_hit_uses_llm_when_not_fast_mode(self):
        original_search = app.search_knowledge
        original_generate = app.generate_with_llm
        calls = []

        def fake_search(_question):
            return [
                {
                    "id": 101,
                    "title": "曼飞龙塔景点资料",
                    "category": "景点讲解",
                    "content": "曼飞龙塔位于五印坛城北侧，适合拍照打卡，随景区开放时间开放。",
                    "score": 99,
                    "sourceType": "official_docx",
                }
            ]

        def fake_generate(messages):
            calls.append(messages)
            return {"content": "曼飞龙塔随景区开放时间开放，建议结合五印坛城一起游览。", "model": "deepseek-chat", "provider": "deepseek"}

        app.search_knowledge = fake_search
        app.generate_with_llm = fake_generate
        try:
            with EnvPatch({"SCENIC_CHAT_FAST_MODE": "false"}):
                result = app.answer_question("景区几点开放？当前选中的景点是：曼飞龙塔。")
        finally:
            app.search_knowledge = original_search
            app.generate_with_llm = original_generate

        self.assertEqual(len(calls), 1)
        self.assertEqual(result["llmProvider"], "deepseek")
        self.assertEqual(result["modelName"], "deepseek-chat")
        self.assertFalse(result["fallback"])
        self.assertIn("曼飞龙塔", calls[0][1]["content"])

    def test_hybrid_search_matches_related_document(self):
        documents = [
            {"id": "1", "title": "开放时间", "category": "服务", "content": "景区开放时间为9:00到17:00。"},
            {"id": "2", "title": "九龙灌浴", "category": "演艺", "content": "九龙灌浴平日演出时间为10:00、11:30、13:30、15:00。"},
        ]
        result = search_engine.search_documents("九龙灌浴什么时候表演？", documents, limit=1)
        self.assertEqual(result[0]["id"], "2")
        self.assertGreater(result[0]["score"], 0)

    def test_behavior_analytics_reads_excel_baseline(self):
        result = app.build_behavior_analytics()
        self.assertTrue(result["available"])
        self.assertEqual(result["rowCount"], 140447)
        self.assertEqual(result["matchedScenicRows"], 777)
        self.assertTrue(result["structuredTableImported"])
        self.assertEqual(result["structuredTableName"], "behavior_visit_record")
        self.assertEqual(result["analysisScope"], "长三角景区行为样本参考")
        self.assertIn("景点景区旅游数据行为分析数据.xlsx", result["sampleSourceFile"])
        self.assertIn("灵山", result["scenicMatchedKeywords"])
        self.assertIn("官方 DOCX", result["lingshanDocumentSource"])
        self.assertEqual(result["dateRange"]["start"], "2025-01-01")
        self.assertEqual(result["dateRange"]["end"], "2025-12-31")
        self.assertEqual(result["dataSource"]["label"], "长三角景区行为样本参考")

    def test_streaming_chunks_and_sse_event(self):
        chunks = streaming.chunk_text("九龙灌浴表演开始。建议提前到场。", max_chars=8)
        self.assertGreaterEqual(len(chunks), 2)
        event = streaming.sse_event("delta", {"text": chunks[0]})
        self.assertIn("event: delta", event)
        self.assertIn("data:", event)

    def test_stream_chat_record_closes_connection(self):
        class DummyHandler:
            def __init__(self):
                self.wfile = io.BytesIO()
                self.headers = []
                self.close_connection = False

            def send_response(self, status):
                self.status = status

            def send_header(self, key, value):
                self.headers.append((key, value))

            def end_headers(self):
                pass

        handler = DummyHandler()
        record = {
            "id": "chat-1",
            "question": "九龙灌浴什么时候表演？",
            "answer": "九龙灌浴平日演出时间为10:00、11:30、13:30、15:00。",
        }
        app.stream_chat_record(handler, record)
        body = handler.wfile.getvalue().decode("utf-8")
        self.assertEqual(handler.status, 200)
        self.assertIn(("Connection", "close"), handler.headers)
        self.assertIn("event: done", body)
        self.assertTrue(handler.close_connection)


class BackendHttpTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = ROOT / ".tmp" / f"backend-test-{os.getpid()}-{id(self)}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.original_db_path = app.DB_PATH
        self.original_data_dir = app.DATA_DIR
        self.original_rate_buckets = app.RATE_LIMIT_BUCKETS
        app.DATA_DIR = self.temp_dir
        app.DB_PATH = self.temp_dir / "test_scenic_guide.db"
        app.RATE_LIMIT_BUCKETS = {}
        app.init_database()

        self.env_patch = EnvPatch(
            {
                "SCENIC_ADMIN_TOKEN": "unit-test-admin-token",
                "SCENIC_CHAT_FAST_MODE": "true",
                "SCENIC_LLM_PROVIDER": "dashscope",
                "SCENIC_LLM_API_KEY": None,
                "DASHSCOPE_API_KEY": None,
                "BAILIAN_API_KEY": None,
                "SCENIC_VISION_PROVIDER": "dashscope",
                "SCENIC_VISION_MODEL": "qwen3-vl-plus",
                "SCENIC_VISION_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "SCENIC_VISION_API_KEY": None,
            }
        )
        self.env_patch.__enter__()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.ScenicGuideHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.env_patch.__exit__(None, None, None)
        app.DB_PATH = self.original_db_path
        app.DATA_DIR = self.original_data_dir
        app.RATE_LIMIT_BUCKETS = self.original_rate_buckets
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def request(self, method, path, body=None, headers=None):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json", **(headers or {})},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.headers, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, exc.read().decode("utf-8")

    def test_admin_write_without_token_fails(self):
        status, _headers, body = self.request(
            "POST",
            "/api/admin/knowledge",
            {"title": "测试知识", "category": "测试", "content": "测试内容"},
        )
        data = json.loads(body)
        self.assertEqual(status, 401)
        self.assertEqual(data["code"], "admin_token_invalid")

    def test_admin_write_with_token_succeeds(self):
        status, _headers, body = self.request(
            "POST",
            "/api/admin/knowledge",
            {"title": "单元测试知识", "category": "测试", "content": "单元测试内容"},
            {"X-Admin-Token": "unit-test-admin-token"},
        )
        data = json.loads(body)
        self.assertEqual(status, 201)
        self.assertEqual(data["title"], "单元测试知识")
        self.assertEqual(data["sourceType"], "manual")

    def test_admin_read_without_token_fails(self):
        status, _headers, body = self.request("GET", "/api/admin/operations/overview")
        data = json.loads(body)
        self.assertEqual(status, 401)
        self.assertEqual(data["code"], "admin_token_invalid")

    def test_admin_read_with_token_succeeds(self):
        status, _headers, body = self.request(
            "GET",
            "/api/admin/operations/overview",
            headers={"X-Admin-Token": "unit-test-admin-token"},
        )
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(data["available"])

    def test_spot_location_code_can_resolve_anchor(self):
        anchor = next(
            spot
            for spot in app.get_spots()
            if spot.get("verifiedLocation") and spot.get("locationCode")
        )
        status, _headers, body = self.request("GET", f"/api/location/resolve?code={anchor['locationCode']}")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["anchor"]["id"], anchor["id"])
        self.assertEqual(data["confidence"], "high")

    def test_nearby_location_returns_quality_message(self):
        anchor = next(
            spot
            for spot in app.get_spots()
            if spot.get("verifiedLocation") and spot.get("lat") and spot.get("lon")
        )
        status, _headers, body = self.request(
            "GET",
            f"/api/spots/nearby?lat={anchor['lat']}&lon={anchor['lon']}&accuracy=12&limit=2",
        )
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["confidence"], "high")
        self.assertTrue(data["insideScenic"])
        self.assertEqual(data["nearest"]["id"], anchor["id"])
        self.assertGreaterEqual(len(data["items"]), 1)
        self.assertTrue(data["message"])

    def test_cors_allows_configured_frontend_origin(self):
        status, headers, _body = self.request(
            "GET",
            "/api/llm/status",
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:5173")

    def test_cors_does_not_echo_unknown_origin(self):
        status, headers, _body = self.request(
            "GET",
            "/api/llm/status",
            headers={"Origin": "https://example.invalid"},
        )
        self.assertEqual(status, 200)
        self.assertIsNone(headers.get("Access-Control-Allow-Origin"))

    def test_chat_stream_endpoint_returns_sse(self):
        status, headers, body = self.request("POST", "/api/chat/stream", {"question": "景区几点开放？"})
        self.assertEqual(status, 200)
        self.assertIn("text/event-stream", headers.get("Content-Type", ""))
        self.assertIn("event: delta", body)
        self.assertIn("event: done", body)

    def test_vision_endpoint_rejects_invalid_image(self):
        data = base64.b64encode(b"<svg></svg>").decode("ascii")
        status, _headers, body = self.request(
            "POST",
            "/api/vision/analyze",
            {"image": f"data:image/svg+xml;base64,{data}"},
        )
        payload = json.loads(body)
        self.assertEqual(status, 400)
        self.assertEqual(payload["code"], "validation_error")

    def test_vision_endpoint_missing_key_returns_config_hint(self):
        data = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii")
        status, _headers, body = self.request(
            "POST",
            "/api/vision/analyze",
            {"image": f"data:image/png;base64,{data}", "question": "这是什么景点？"},
        )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(payload["fallback"])
        self.assertEqual(payload["llmProvider"], "dashscope")
        self.assertEqual(payload["modelName"], "qwen3-vl-plus")
        self.assertIn("SCENIC_VISION_API_KEY", payload["answer"])
        self.assertIn("DASHSCOPE_API_KEY", payload["answer"])

    def test_llm_status_missing_key(self):
        status, _headers, body = self.request("GET", "/api/llm/status")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"], "missing_api_key")
        self.assertEqual(payload["visionProvider"], "dashscope")
        self.assertFalse(payload["visionAvailable"])
        self.assertEqual(payload["visionReason"], "missing_api_key")

    def test_system_capabilities_endpoint_reports_targets(self):
        status, _headers, body = self.request("GET", "/api/system/capabilities")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(payload["coreAi"]["multimodalRequired"])
        self.assertEqual(payload["coreAi"]["multimodalModel"], "qwen3-vl-plus")
        self.assertTrue(payload["knowledge"]["localKnowledgeEnabled"])
        self.assertGreater(payload["knowledge"]["activeDocuments"], 0)
        self.assertEqual(payload["quality"]["voiceQaLatencyTargetMs"], 5000)
        self.assertTrue(payload["positioning"]["gpsSupported"])

    def test_mobile_entry_is_served_by_backend(self):
        status, headers, body = self.request("GET", "/mobile/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn("灵山胜境移动导览", body)

    def test_chat_endpoint_returns_latency_ms(self):
        status, _headers, body = self.request("POST", "/api/chat", {"question": "景区几点开放？"})
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("latencyMs", payload)
        self.assertIsInstance(payload["latencyMs"], int)
        self.assertGreaterEqual(payload["latencyMs"], 0)

    def test_known_spot_location_is_corrected_on_init(self):
        with app.get_connection() as connection:
            connection.execute(
                "UPDATE scenic_spot SET lat = ?, lon = ? WHERE name = ?",
                (29.5617, 106.5511, "游客服务中心"),
            )
        app.init_database()
        service_center = next(spot for spot in app.get_spots(include_inactive=True) if spot["name"] == "游客服务中心")
        self.assertAlmostEqual(service_center["lat"], 31.4282, places=4)
        self.assertAlmostEqual(service_center["lon"], 120.0951, places=4)
        self.assertEqual(service_center["mapZone"], "lingshan")
        self.assertTrue(service_center["verifiedLocation"])

    def test_reference_spot_coordinates_are_corrected_on_init(self):
        spots = {spot["name"]: spot for spot in app.get_spots(include_inactive=True)}
        self.assertAlmostEqual(spots["灵山大佛"]["lat"], 31.43194, places=5)
        self.assertAlmostEqual(spots["灵山大佛"]["lon"], 120.09139, places=5)
        self.assertAlmostEqual(spots["灵山梵宫"]["lat"], 31.4303, places=4)
        self.assertAlmostEqual(spots["灵山梵宫"]["lon"], 120.0974, places=4)

    def test_recommended_routes_do_not_cross_map_zones(self):
        lingshan_route = app.recommend_route(180, "佛教文化")
        nianhua_route = app.recommend_route(180, "餐饮购物")
        relaxed_route = app.recommend_route(180, "轻松休闲")

        self.assertTrue(lingshan_route["spots"])
        self.assertTrue(nianhua_route["spots"])
        self.assertTrue(relaxed_route["spots"])
        self.assertEqual({spot["mapZone"] for spot in lingshan_route["spots"]}, {"lingshan"})
        self.assertEqual({spot["mapZone"] for spot in nianhua_route["spots"]}, {"nianhua"})
        self.assertEqual({spot["mapZone"] for spot in relaxed_route["spots"]}, {"nianhua"})

    def test_official_route_templates_are_loaded_from_guide_docx(self):
        templates = app.load_official_route_templates(app.get_spots())
        titles = {template["title"]: template for template in templates}
        self.assertIn("历史文化爱好者路线", titles)
        self.assertIn("自然风光爱好者路线", titles)
        self.assertIn("亲子家庭路线", titles)
        self.assertEqual(titles["历史文化爱好者路线"]["duration"], 360)
        self.assertIn("灵山大佛", titles["历史文化爱好者路线"]["spotSequence"])
        self.assertIn("九龙灌浴", titles["亲子家庭路线"]["spotSequence"])

    def test_official_documents_include_full_text_without_blocking_on_empty_behavior_table(self):
        original_iter_xlsx_rows = app.iter_xlsx_rows

        def fail_if_excel_scanned(_path):
            raise AssertionError("empty behavior table should not synchronously scan Excel")

        app.iter_xlsx_rows = fail_if_excel_scanned
        try:
            documents = app.build_official_knowledge_documents(app.parse_official_spot_records())
            behavior_result = app.build_behavior_analytics()
        finally:
            app.iter_xlsx_rows = original_iter_xlsx_rows

        full_text_documents = [document for document in documents if document["category"] == "官方资料全文"]
        behavior_titles = {document["title"] for document in documents if document["sourceType"] == "behavior_excel"}

        self.assertGreaterEqual(len(full_text_documents), 2)
        self.assertNotIn("官方资料包：长三角景区行为样本参考摘要", behavior_titles)
        self.assertFalse(behavior_result["available"])
        self.assertEqual(behavior_result["dataSource"]["type"], "behavior_table_pending")

    def test_behavior_summary_document_is_available_after_structured_import(self):
        with app.get_connection() as connection:
            app.sync_behavior_visit_records(connection)
        documents = app.build_official_knowledge_documents(app.parse_official_spot_records())
        behavior_titles = {document["title"] for document in documents if document["sourceType"] == "behavior_excel"}

        self.assertIn("官方资料包：长三角景区行为样本参考摘要", behavior_titles)
        self.assertTrue(any("全量记录数" in document["content"] for document in documents))

    def test_recommended_lingshan_routes_prefer_official_templates(self):
        history_route = app.recommend_route(300, "历史文化")
        nature_route = app.recommend_route(300, "自然风光")
        family_route = app.recommend_route(240, "亲子游")

        self.assertEqual(history_route["sourceType"], "official_docx")
        self.assertEqual(history_route["officialRouteDuration"], 360)
        self.assertEqual([spot["name"] for spot in history_route["spots"]], ["灵山大照壁", "祥符禅寺", "灵山大佛", "灵山梵宫", "五印坛城"])
        self.assertEqual(nature_route["sourceType"], "official_docx")
        self.assertIn("曼飞龙塔", [spot["name"] for spot in nature_route["spots"]])
        self.assertEqual(family_route["sourceType"], "official_docx")
        self.assertEqual([spot["name"] for spot in family_route["spots"]], ["九龙灌浴", "百子戏弥勒", "灵山梵宫", "五印坛城"])

    def test_recommended_routes_follow_map_path_order(self):
        lingshan_route = app.recommend_route(240, "佛教文化")
        nianhua_route = app.recommend_route(180, "轻松休闲")

        lingshan_orders = [app.route_order_key(spot, "lingshan")[0] for spot in lingshan_route["spots"]]
        nianhua_orders = [app.route_order_key(spot, "nianhua")[0] for spot in nianhua_route["spots"]]

        self.assertEqual(lingshan_orders, sorted(lingshan_orders))
        self.assertEqual(nianhua_orders, sorted(nianhua_orders))

    def test_routes_options_include_relaxed_preference(self):
        status, _headers, body = self.request("GET", "/api/routes/options")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("轻松休闲", payload["preferences"])

    def test_asr_status_defaults_to_text_fallback(self):
        status, _headers, body = self.request("GET", "/api/asr/status")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["fallback"], "text_input")

    def test_admin_public_data_reimport_with_token_returns_summary(self):
        status, _headers, body = self.request(
            "POST",
            "/api/admin/public-data/reimport",
            {},
            {"X-Admin-Token": "unit-test-admin-token"},
        )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("spotCount", payload)
        self.assertIn("knowledgeCount", payload)
        self.assertIsNone(payload.get("behaviorRecordCount"))
        self.assertIn("message", payload)

    def test_behavior_excel_can_import_to_structured_table(self):
        with app.get_connection() as connection:
            summary = app.sync_behavior_visit_records(connection)
            row = connection.execute("SELECT COUNT(*) AS count FROM behavior_visit_record").fetchone()
        analytics = app.build_behavior_analytics_from_table()
        self.assertGreater(summary["behaviorRecordCount"], 0)
        self.assertEqual(row["count"], summary["behaviorRecordCount"])
        self.assertIsNotNone(analytics)
        self.assertEqual(analytics["dataSource"]["type"], "behavior_table")
        self.assertEqual(analytics["rowCount"], summary["behaviorRecordCount"])
        self.assertEqual(analytics["matchedScenicRows"], 777)
        self.assertEqual(analytics["analysisScope"], "长三角景区行为样本参考")

        with app.get_connection() as connection:
            connection.execute("UPDATE import_metadata SET value = 'stale-signature' WHERE key LIKE 'behavior_visit_record:%'")
        stale_analytics = app.build_behavior_analytics_from_table()
        self.assertIsNotNone(stale_analytics)
        self.assertEqual(stale_analytics["rowCount"], summary["behaviorRecordCount"])
        self.assertFalse(stale_analytics["structuredTableCurrent"])

    def test_admin_low_confidence_chat_can_become_knowledge_draft(self):
        app.save_chat_record(
            {
                "id": "low-confidence-chat",
                "question": "游客中心有没有儿童推车？",
                "answer": "资料不足，请咨询游客服务中心。",
                "relatedSpots": [],
                "sourceRefs": [],
                "intent": "交通服务",
                "confidence": 0.41,
                "sentiment": "neutral",
                "createdAt": 1234567890,
            }
        )
        status, _headers, body = self.request(
            "POST",
            "/api/admin/knowledge/from-chat",
            {"chatId": "low-confidence-chat"},
            {"X-Admin-Token": "unit-test-admin-token"},
        )
        payload = json.loads(body)
        self.assertEqual(status, 201)
        self.assertEqual(payload["status"], "inactive")
        self.assertIn("游客中心有没有儿童推车？", payload["content"])

    def test_inactive_knowledge_is_not_used_by_search(self):
        inactive = app.create_knowledge(
            {
                "title": "隐藏测试资料",
                "category": "测试",
                "content": "uniqueterminactive 这条资料不应该参与游客问答。",
                "status": "inactive",
            }
        )
        hits = app.search_knowledge("uniqueterminactive")
        self.assertNotIn(inactive["id"], {hit["id"] for hit in hits})


if __name__ == "__main__":
    unittest.main()
