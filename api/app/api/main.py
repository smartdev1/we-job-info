"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.offers import router as offers_router
from app.api.routes.templates import router as templates_router
from app.api.routes.copywriting import router as copywriting_router
from app.api.routes.publishing import router as publishing_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="we-info-jobs API", version="0.1.0", debug=settings.app_env == "development")

    allowed_origins = [settings.front_base_url]
    if settings.app_env == "development":
        allowed_origins += ["http://localhost:3000", "http://127.0.0.1:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(offers_router, prefix="/api/v1")
    app.include_router(templates_router, prefix="/api/v1")
    app.include_router(copywriting_router, prefix="/api/v1")
    app.include_router(publishing_router, prefix="/api/v1")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()