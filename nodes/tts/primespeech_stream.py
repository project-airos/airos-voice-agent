"""PrimeSpeech streaming node skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class PrimeSpeechConfig:
    """Configuration for the PrimeSpeech TTS node."""

    voice: str = "zh-CN-female-1"


class PrimeSpeechStreamNode:
    """Placeholder streaming TTS node."""

    def __init__(self, config: PrimeSpeechConfig | None = None) -> None:
        self.config = config or PrimeSpeechConfig()

    def synthesize(self, text_stream: Iterable[str]) -> Iterable[bytes]:
        """Yield encoded audio frames."""

        raise NotImplementedError("PrimeSpeechStreamNode.synthesize requires implementation")
