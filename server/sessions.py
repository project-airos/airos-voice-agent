"""Session lifecycle management for lecture interactions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

from fastapi import HTTPException, status

from .models import SessionCreateRequest, SessionInfo


@dataclass(slots=True)
class SessionRecord:
    """Stored metadata for an active session."""

    info: SessionInfo
    connected: bool = False


class SessionManager:
    """In-memory registry for active lecture sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionRecord] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, request: SessionCreateRequest) -> SessionInfo:
        """Create a new session for a given lecture."""

        async with self._lock:
            session_id = f"sess_{uuid4().hex[:12]}"
            info = SessionInfo(
                session_id=session_id,
                lecture_id=request.lecture_id,
                locale=request.locale,
                mode=request.mode,
                created_at=datetime.now(tz=timezone.utc),
            )
            self._sessions[session_id] = SessionRecord(info=info)
            return info

    async def get(self, session_id: str) -> SessionInfo:
        """Fetch session metadata or raise an HTTP 404 error."""

        async with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Unknown session_id '{session_id}'",
                )
            return record.info

    async def mark_connected(self, session_id: str) -> None:
        """Mark a session as having an attached websocket."""

        async with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Unknown session_id '{session_id}'",
                )
            record.connected = True

    async def detach(self, session_id: str) -> None:
        """Mark the websocket as disconnected."""

        async with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return
            record.connected = False

    async def list_sessions(self) -> list[SessionInfo]:
        """Return all active session metadata."""

        async with self._lock:
            return [record.info for record in self._sessions.values()]
