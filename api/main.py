import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.security import auth_enabled, is_dev, require_api_key
from src.knowledge.seed import seed_knowledge_base, warn_if_empty
from src.utils.logging_config import setup_logging
from src.utils.paths import InvalidPathError

setup_logging()

# Volume Railway mount vao /app/knowledge_base va che noi dung trong image.
# Nap seed vao volume trong lan chay dau, chi cho file con thieu.
seed_knowledge_base()
warn_if_empty()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Marketing Agent API",
    description="AI-powered social media campaign generator",
    version="0.1.0",
)

# CORS: production serve SPA cùng origin nên không cần cross-origin.
# Chỉ mở cho dev server của Vite, hoặc danh sách trong ALLOWED_ORIGINS.
_DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,  # auth qua header X-API-Key, không dùng cookie
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.exception_handler(InvalidPathError)
async def invalid_path_handler(request: Request, exc: InvalidPathError):
    """Id/path không an toàn từ client → 400, không lộ đường dẫn thật của server."""
    return JSONResponse(status_code=400, content={"detail": {"message": str(exc)}})


# Include routers — tất cả đều yêu cầu API key
from api.routes.campaign import router as campaign_router
from api.routes.brands import router as brands_router
from api.routes.templates import router as templates_router

_protected = [Depends(require_api_key)]

app.include_router(
    campaign_router, prefix="/api/campaigns", tags=["campaigns"], dependencies=_protected
)
app.include_router(
    brands_router, prefix="/api/brands", tags=["brands"], dependencies=_protected
)
app.include_router(
    templates_router, prefix="/api/templates", tags=["templates"], dependencies=_protected
)


@app.get("/api/health")
def health():
    """Public — Railway healthcheck gọi endpoint này."""
    return {"status": "ok"}


@app.get("/api/auth/status")
def auth_status():
    """
    Public — frontend hỏi có cần nhập access key không.

    misconfigured=True nghĩa là đang chạy production mà thiếu APP_API_KEY:
    mọi endpoint /api sẽ trả 503, frontend hiện cảnh báo cho admin.
    """
    enabled = auth_enabled()
    return {"auth_required": enabled, "misconfigured": not enabled and not is_dev()}


@app.get("/api/auth/verify", dependencies=_protected)
def auth_verify():
    """Protected — frontend dùng để kiểm tra key user vừa nhập."""
    return {"valid": True}


# Serve React static files
DIST_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"

if DIST_DIR.exists():
    # Serve static assets (js, css, images)
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    # Catch-all: serve index.html for any non-API route (SPA routing).
    # Không bảo vệ bằng API key — đây chỉ là vỏ frontend, mọi dữ liệu đều
    # nằm sau /api/* đã được bảo vệ.
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        # /api/* không khớp route nào → 404 JSON, không trả vỏ SPA.
        # Nếu không chặn, client gọi sai endpoint sẽ nhận HTML kèm 200.
        if path.startswith("api/"):
            return JSONResponse(
                status_code=404, content={"detail": {"message": "Endpoint không tồn tại"}}
            )
        try:
            file_path = (DIST_DIR / path).resolve()
            if DIST_DIR.resolve() in file_path.parents and file_path.is_file():
                return FileResponse(file_path)
        except (OSError, ValueError):
            logger.debug("Path SPA không hợp lệ, trả index.html: %r", path)
        return FileResponse(DIST_DIR / "index.html")
