"""WebSocket publisher node skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class WebSocketPublisherConfig:
    """Configuration for outbound WebSocket publishing."""

    url: str = "ws://localhost:8000/ws"


class WebSocketPublisherNode:
    """Send structured events to connected WebSocket clients."""

    def __init__(self, config: WebSocketPublisherConfig | None = None) -> None:
        self.config = config or WebSocketPublisherConfig()

    async def send(self, message: Dict[str, Any]) -> None:
        """Serialize and send the given payload."""

        raise NotImplementedError("WebSocketPublisherNode.send requires implementation")
