from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

import app_core as core
from routes.api_router import dispatch


class ScenicGuideHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        core.send_cors_headers(self)
        self.end_headers()

    def do_GET(self):
        self._handle_request("GET")

    def do_POST(self):
        self._handle_request("POST")

    def do_PUT(self):
        self._handle_request("PUT")

    def do_DELETE(self):
        self._handle_request("DELETE")

    def _handle_request(self, method):
        try:
            path = urlparse(self.path).path
            if method == "GET":
                if core.is_admin_api(path) and not core.has_valid_admin_token(self):
                    core.error_response(self, "admin token invalid or missing", 401, "admin_token_invalid")
                    return
                if core.is_admin_api(path) and core.rate_limit_exceeded(self, "admin", 120, 60):
                    core.error_response(self, "too many admin requests", 429, "rate_limited")
                    return
            else:
                if core.is_admin_mutation(path, method) and not core.has_valid_admin_token(self):
                    core.error_response(self, "admin token invalid or missing", 401, "admin_token_invalid")
                    return
                if path in {"/api/chat", "/api/chat/stream"} and core.rate_limit_exceeded(self, "chat", 30, 60):
                    core.error_response(self, "too many chat requests", 429, "rate_limited")
                    return
                if path == "/api/vision/analyze" and core.rate_limit_exceeded(self, "vision", 8, 60):
                    core.error_response(self, "too many vision requests", 429, "rate_limited")
                    return
                if path == "/api/asr/transcribe" and core.rate_limit_exceeded(self, "asr", 12, 60):
                    core.error_response(self, "too many ASR requests", 429, "rate_limited")
                    return
                if path == "/api/tts/synthesize" and core.rate_limit_exceeded(self, "tts", 20, 60):
                    core.error_response(self, "too many TTS requests", 429, "rate_limited")
                    return
                if core.is_admin_mutation(path, method) and core.rate_limit_exceeded(self, "admin", 80, 60):
                    core.error_response(self, "too many admin requests", 429, "rate_limited")
                    return

            dispatch(method, self)
        except ValueError as exc:
            core.error_response(self, str(exc), 400, "validation_error")
        except Exception as exc:
            print(f"[ERROR] {method} {self.path}: {exc}")
            core.error_response(self, "internal service error", 500, "internal_error")

    def log_message(self, format, *args):
        print(f"[{core.time.strftime('%H:%M:%S')}] {self.address_string()} {format % args}")
