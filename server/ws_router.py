"""WebSocket endpoint wiring for the lecture demo server."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .dataflow import DataflowAdapter
from .sessions import SessionManager

LOGGER = logging.getLogger(__name__)


def create_ws_router(
    session_manager: SessionManager, dataflow: DataflowAdapter
) -> APIRouter:
    """Create a router that exposes the WebSocket session endpoint."""

    router = APIRouter()

    @router.websocket("/ws/{session_id}")
    async def session_socket(websocket: WebSocket, session_id: str) -> None:
        await session_manager.get(session_id)
        await session_manager.mark_connected(session_id)
        await dataflow.ensure_session(session_id)
        await websocket.accept()
        sender = asyncio.create_task(
            _forward_server_messages(websocket, dataflow, session_id)
        )
        try:
            while True:
                payload = await websocket.receive_json()
                await dataflow.route_inbound(session_id, payload)
        except WebSocketDisconnect:
            LOGGER.info("WebSocket disconnected for session %s", session_id)
        finally:
            sender.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sender
            await session_manager.detach(session_id)
            await dataflow.close_session(session_id)

    return router


async def _forward_server_messages(
    websocket: WebSocket, dataflow: DataflowAdapter, session_id: str
) -> None:
    """Forward messages emitted by the dataflow adapter to the client."""

    try:
        while True:
            message = await dataflow.next_outbound(session_id)
            await websocket.send_json(message.model_dump())
    except asyncio.CancelledError:  # pragma: no cover - cancellation path
        pass
