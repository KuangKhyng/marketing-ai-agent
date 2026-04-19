from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(
    title="Marketing Agent API",
    description="AI-powered social media campaign generator",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from api.routes.campaign import router as campaign_router
from api.routes.brands import router as brands_router
from api.routes.templates import router as templates_router

app.include_router(campaign_router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(brands_router, prefix="/api/brands", tags=["brands"])
app.include_router(templates_router, prefix="/api/templates", tags=["templates"])

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Serve React static files
DIST_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"

if DIST_DIR.exists():
    # Serve static assets (js, css, images)
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    # Catch-all: serve index.html for any non-API route (SPA routing)
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = DIST_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
