"""Slide engine node skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SlideCommand:
    """Instruction emitted to the WebSocket publisher."""

    type: str
    section_id: str


@dataclass
class SlideEngineState:
    """Track the current position within the lecture."""

    current_section: str


class SlideEngineNode:
    """Handle navigation events and tutor-initiated branching."""

    def __init__(self, initial_section: str = "intro") -> None:
        self.state = SlideEngineState(current_section=initial_section)

    def handle_control(self, action: str) -> Optional[SlideCommand]:
        """Apply a control action and emit a slide command if needed."""

        raise NotImplementedError("SlideEngineNode.handle_control requires implementation")

    def handle_branch(self, branch_id: str) -> Optional[SlideCommand]:
        """Return a slide command directing the client to a branch."""

        raise NotImplementedError("SlideEngineNode.handle_branch requires implementation")
