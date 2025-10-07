"""WebSocket ingress node stub for Dora integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class WebSocketServerConfig:
    """Configuration for the WebSocket ingress node."""

    host: str = "0.0.0.0"
    port: int = 8765
    path: str = "/ws"


class WebSocketServerNode:
    """Skeleton implementation for the Dora WebSocket ingress node."""

    def __init__(self, config: WebSocketServerConfig | None = None) -> None:
        self.config = config or WebSocketServerConfig()

    async def run(self) -> None:  # pragma: no cover - placeholder method
        """Start accepting client connections and emit Dora events."""

        raise NotImplementedError(
            "WebSocketServerNode.run must be implemented to bridge Dora inputs."
        )

    async def publish_audio(self, frame: bytes) -> None:
        """Publish raw PCM audio into the Dora graph."""

        raise NotImplementedError

    async def publish_text(self, message: Dict[str, Any]) -> None:
        """Publish text/control payloads into the Dora graph."""

        raise NotImplementedError
