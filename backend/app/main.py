import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import Base, engine
from .routers import auth as auth_router
from .routers import projects as projects_router
from .routers import admin as admin_router

Base.metadata.create_all(bind=engine)  # creates specgen.db tables on first run

app = FastAPI(
    title="SpecGen AI",
    description="AI-assisted platform for generating software requirement specifications.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(projects_router.router)
app.include_router(admin_router.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": "SpecGen AI",
        "version": "2.0.0",
        "environment": os.environ.get("ENVIRONMENT", "production"),
    }


# Production SPA Frontend mounting (if built static files are present)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))

