import sys
import os

# Ensure the root directory is on the path so app modules can be imported
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Also add authdesk-kit fallback
kit_dir = os.path.join(ROOT_DIR, "authdesk-kit")
if os.path.exists(kit_dir) and kit_dir not in sys.path:
    sys.path.insert(0, kit_dir)

try:
    from app.main import app
except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import traceback
    app = FastAPI(title="AuthDesk [Startup Error]")
    err_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        return JSONResponse(status_code=500, content={"error": "Startup error", "detail": err_msg})
