"""Local memory node skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class MemoryQuery:
    """Query structure for retrieving contextual snippets."""

    text: str
    top_k: int = 5


@dataclass
class MemoryEntry:
    """Stored snippet information."""

    key: str
    value: str
    ttl_seconds: int | None = None


class LocalMemoryNode:
    """Minimal interface for a vector-backed memory component."""

    def query(self, request: MemoryQuery) -> List[str]:
        """Return top-k snippets for the provided query."""

        raise NotImplementedError("LocalMemoryNode.query requires implementation")

    def write(self, entry: MemoryEntry) -> None:
        """Persist a new snippet into the memory store."""

        raise NotImplementedError("LocalMemoryNode.write requires implementation")
