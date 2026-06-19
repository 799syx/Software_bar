import app_core as core


def send_file(handler, file_path):
    content = file_path.read_bytes()
    content_type = core.static_content_type(file_path)
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def serve_static(handler, path):
    if path in ("/", ""):
        file_path = core.FRONTEND_DIR / "index.html"
    else:
        requested = (core.FRONTEND_DIR / path.lstrip("/")).resolve()
        try:
            requested.relative_to(core.FRONTEND_DIR.resolve())
            file_path = requested
        except ValueError:
            file_path = core.FRONTEND_DIR / "index.html"

    if not file_path.exists() or not file_path.is_file():
        file_path = core.FRONTEND_DIR / "index.html"

    send_file(handler, file_path)


def serve_mobile_static(handler, path):
    if path in ("/mobile", "/mobile/"):
        file_path = core.FRONTEND_MOBILE_DIR / "index.html"
    else:
        relative_path = path[len("/mobile/") :].lstrip("/") if path.startswith("/mobile/") else ""
        requested = (core.FRONTEND_MOBILE_DIR / relative_path).resolve()
        try:
            requested.relative_to(core.FRONTEND_MOBILE_DIR.resolve())
            file_path = requested
        except ValueError:
            file_path = core.FRONTEND_MOBILE_DIR / "index.html"

    if not file_path.exists() or not file_path.is_file():
        file_path = core.FRONTEND_MOBILE_DIR / "index.html"

    send_file(handler, file_path)


def serve_public_asset(handler, path):
    relative_path = path[len("/assets/") :].lstrip("/")
    requested = (core.PUBLIC_ASSETS_DIR / relative_path).resolve()
    try:
        requested.relative_to(core.PUBLIC_ASSETS_DIR.resolve())
        file_path = requested
    except ValueError:
        core.error_response(handler, "invalid asset path", 400, "invalid_asset_path")
        return

    if not file_path.exists() or not file_path.is_file():
        serve_static(handler, path)
        return

    send_file(handler, file_path)
