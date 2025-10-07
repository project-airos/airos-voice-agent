"""Voice activity detection node skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class SpeechMonitorConfig:
    """Configuration for the speech monitor node."""

    sample_rate: int = 16000
    frame_ms: int = 30


class SpeechMonitorNode:
    """Placeholder VAD node awaiting concrete integration."""

    def __init__(self, config: SpeechMonitorConfig | None = None) -> None:
        self.config = config or SpeechMonitorConfig()

    def process(self, frames: Iterable[bytes]) -> Iterable[bytes]:
        """Split raw PCM frames into voiced segments."""

        raise NotImplementedError("SpeechMonitorNode.process requires implementation")
