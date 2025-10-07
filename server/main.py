"""Application factory for the lecture demo server."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from .config import Settings, get_settings
from .dataflow import DataflowAdapter
from .http_api import create_http_router
from .lecture_store import LectureStore
from .sessions import SessionManager
from .ws_router import create_ws_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a fully configured FastAPI application."""

    settings = settings or get_settings()
    session_manager = SessionManager()
    lecture_store = LectureStore(Path(settings.lecture_config_dir))
    dataflow = DataflowAdapter()

    app = FastAPI(title="Airos Voice Agent Demo Server", version=settings.version)
    app.include_router(create_http_router(settings, session_manager, lecture_store))
    app.include_router(create_ws_router(session_manager, dataflow))

    return app


app = create_app()
