"""Intent router node skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class IntentResult:
    """Structured output from the intent router."""

    question: str | None = None
    control: str | None = None
    smalltalk: str | None = None


class IntentRouterNode:
    """Route text utterances to question/control/smalltalk streams."""

    def classify(self, text_stream: Iterable[str]) -> Iterable[IntentResult]:
        """Map each utterance to one of the supported intents."""

        raise NotImplementedError("IntentRouterNode.classify requires implementation")
