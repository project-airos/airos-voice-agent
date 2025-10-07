"""Placeholder dataflow adapter that mimics Dora integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict

from pydantic import TypeAdapter

from .ws_messages import ClientMessage, ServerMessage, SlideGoto, TutorAnswerText

LOGGER = logging.getLogger(__name__)

_client_adapter = TypeAdapter(ClientMessage)
_server_adapter = TypeAdapter(ServerMessage)


@dataclass(slots=True)
class SessionChannels:
    """Queues used to communicate with websocket endpoints."""

    outbound: "asyncio.Queue[ServerMessage]"


class DataflowAdapter:
    """Bridge between the HTTP/WebSocket API and the Dora runtime."""

    def __init__(self) -> None:
        self._channels: Dict[str, SessionChannels] = {}
        self._lock = asyncio.Lock()

    async def ensure_session(self, session_id: str) -> SessionChannels:
        """Create channel queues for a session if they do not exist."""

        async with self._lock:
            channel = self._channels.get(session_id)
            if channel is None:
                channel = SessionChannels(outbound=asyncio.Queue())
                self._channels[session_id] = channel
            return channel

    async def close_session(self, session_id: str) -> None:
        """Remove queues associated with a session."""

        async with self._lock:
            self._channels.pop(session_id, None)

    async def route_inbound(self, session_id: str, payload: dict) -> None:
        """Handle inbound WebSocket messages.

        For now this implementation emits synthetic responses so that the
        server can be exercised end-to-end before the Dora graph is wired up.
        """

        message = _client_adapter.validate_python(payload)
        LOGGER.debug("Inbound WS message: %s", message)

        if message.type == "user.question.text":
            await self._simulate_tutor_answer(session_id, message.text)
        elif message.type == "user.control":
            await self._simulate_slide_response(session_id, message.action)
        else:
            LOGGER.debug("No-op handler for message type %s", message.type)

    async def _simulate_tutor_answer(self, session_id: str, text: str) -> None:
        channel = await self.ensure_session(session_id)
        response = TutorAnswerText(
            text=(
                "(stub) 我已经收到你的问题：“" + text + "”。完整的数据流集成将填充实际回答。"
            )
        )
        await channel.outbound.put(response)

    async def _simulate_slide_response(self, session_id: str, action: str) -> None:
        channel = await self.ensure_session(session_id)
        section_id = "intro" if action == "prev" else "quadratic_formula"
        response = SlideGoto(section_id=section_id)
        await channel.outbound.put(response)

    async def next_outbound(self, session_id: str) -> ServerMessage:
        """Await the next outbound message destined for the client."""

        channel = await self.ensure_session(session_id)
        message = await channel.outbound.get()
        return _server_adapter.validate_python(message)
