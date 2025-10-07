"""HTTP routes for the lecture demo server."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .config import Settings
from .lecture_store import BranchNotFoundError, LectureNotFoundError, LectureStore
from .models import (
    BranchResponse,
    HealthResponse,
    Lecture,
    SessionCreateRequest,
    SessionCreateResponse,
)
from .sessions import SessionManager


def create_http_router(
    settings: Settings, session_manager: SessionManager, lectures: LectureStore
) -> APIRouter:
    """Build the HTTP API router."""

    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(ok=True, version=settings.version)

    @router.post("/sessions", response_model=SessionCreateResponse)
    async def create_session(payload: SessionCreateRequest) -> SessionCreateResponse:
        try:
            lectures.get_lecture(payload.lecture_id)
        except LectureNotFoundError as exc:  # pragma: no cover - validation path
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown lecture_id '{payload.lecture_id}'",
            ) from exc
        session = await session_manager.create_session(payload)
        ws_url = settings.ws_url_template.format(session_id=session.session_id)
        return SessionCreateResponse(session_id=session.session_id, ws_url=ws_url)

    @router.get("/lectures/{lecture_id}", response_model=Lecture)
    async def get_lecture(lecture_id: str) -> Lecture:
        try:
            return lectures.get_lecture(lecture_id)
        except LectureNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown lecture_id '{lecture_id}'",
            ) from exc

    @router.get("/lectures/{lecture_id}/branch/{branch_id}", response_model=BranchResponse)
    async def get_branch(lecture_id: str, branch_id: str) -> BranchResponse:
        try:
            branch = lectures.get_branch(lecture_id, branch_id)
        except (LectureNotFoundError, BranchNotFoundError) as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown branch '{branch_id}' for lecture '{lecture_id}'",
            ) from exc
        return BranchResponse(lecture_id=lecture_id, branch=branch)

    return router
