import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

kit_dir = os.path.join(ROOT_DIR, "authdesk-kit")
if os.path.exists(kit_dir) and kit_dir not in sys.path:
    sys.path.insert(0, kit_dir)

try:
    from app.main import app as _app

    # ASGI middleware to normalize paths rewritten by Vercel
    class PathNormalizer:
        def __init__(self, asgi_app):
            self.asgi_app = asgi_app

        async def __call__(self, scope, receive, send):
            if scope.get("type") in ("http", "websocket"):
                path = scope.get("path", "/")
                for prefix in ("/api/index.py", "/api/index", "/api"):
                    if path == prefix:
                        scope["path"] = "/"
                        break
                    elif path.startswith(prefix + "/"):
                        scope["path"] = path[len(prefix):]
                        break
            await self.asgi_app(scope, receive, send)

    app = PathNormalizer(_app)

except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import traceback
    app = FastAPI(title="AuthDesk [Startup Error]")
    err_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def catch_all(full_path: str):
        return JSONResponse(status_code=500, content={"error": "Startup error", "detail": err_msg})
