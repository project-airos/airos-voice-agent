"""Streaming FunASR node skeleton for Dora integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class FunASRStreamConfig:
    """Runtime configuration for FunASR streaming."""

    locale: str = "zh-CN"


class FunASRStreamNode:
    """Placeholder streaming ASR node."""

    def __init__(self, config: FunASRStreamConfig | None = None) -> None:
        self.config = config or FunASRStreamConfig()

    def process(self, segments: Iterable[bytes]) -> Iterable[str]:
        """Yield partial and final transcription strings."""

        raise NotImplementedError("FunASRStreamNode.process requires implementation")
