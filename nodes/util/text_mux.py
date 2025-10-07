"""Text multiplexer node skeleton."""

from __future__ import annotations

from typing import Iterable, Optional


class TextMuxNode:
    """Merges text from direct WS input and ASR final transcripts."""

    def merge(self, ws_text: Iterable[str], asr_text: Iterable[str]) -> Iterable[str]:
        """Yield resolved text utterances."""

        raise NotImplementedError("TextMuxNode.merge requires implementation")
