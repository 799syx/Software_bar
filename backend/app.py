from http.server import ThreadingHTTPServer
from types import ModuleType
import sys

import app_core as _core
from app_core import *  # noqa: F401,F403
from routes.api_router import parse_int_id
from routes.http_handler import ScenicGuideHandler


def main():
    init_database()
    server = ThreadingHTTPServer((HOST, PORT), ScenicGuideHandler)
    print(f"Scenic guide service started: http://{HOST}:{PORT}")
    print(f"SQLite database: {DB_PATH}")
    start_behavior_records_background_sync()
    print("Press Ctrl+C to stop the service")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping service...")
    finally:
        server.server_close()


class _AppModule(ModuleType):
    def __getattr__(self, name):
        try:
            return getattr(_core, name)
        except AttributeError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name != "_core" and hasattr(_core, name):
            setattr(_core, name, value)


sys.modules[__name__].__class__ = _AppModule


if __name__ == "__main__":
    main()
