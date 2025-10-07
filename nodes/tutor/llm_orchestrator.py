"""Tutor orchestration node skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TutorRequest:
    """Structured input for the tutor orchestrator."""

    text: str
    context: list[str]


@dataclass
class TutorResponse:
    """Outputs from the tutor orchestrator."""

    answer_text: str
    branch: Optional[str] = None


class TutorOrchestratorNode:
    """Coordinate LLM prompting and branching decisions."""

    def generate(self, request: TutorRequest) -> TutorResponse:
        """Produce a tutor response for the provided request."""

        raise NotImplementedError("TutorOrchestratorNode.generate requires implementation")
