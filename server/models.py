"""Pydantic models used by the lecture demo server."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class HealthResponse(BaseModel):
    """Simple health check payload."""

    ok: bool = True
    version: str


class SessionCreateRequest(BaseModel):
    """Request payload for creating or attaching to a session."""

    lecture_id: str = Field(description="Lecture configuration identifier")
    locale: str = Field(description="BCP-47 locale tag, e.g. zh-CN")
    mode: Literal["replay", "live"] = Field(description="Lecture playback mode")


class SessionCreateResponse(BaseModel):
    """Response returned when a session is created."""

    session_id: str
    ws_url: str


class SessionInfo(BaseModel):
    """Internal representation of a session."""

    session_id: str
    lecture_id: str
    locale: str
    mode: Literal["replay", "live"]
    created_at: datetime


class LectureSection(BaseModel):
    """Reveal.js compatible section content."""

    id: str
    title: Optional[str] = None
    html: str


class LectureBranch(BaseModel):
    """Optional detour content that can be requested on demand."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    from_section: str = Field(alias="from")
    slides: list[LectureSection] = Field(default_factory=list)


class Lecture(BaseModel):
    """Static lecture metadata and content."""

    id: str
    title: str
    locale: str = Field(default="zh-CN")
    sections: list[LectureSection]
    branches: list[LectureBranch] = Field(default_factory=list)


class BranchResponse(BaseModel):
    """Response payload for branch content."""

    lecture_id: str
    branch: LectureBranch
