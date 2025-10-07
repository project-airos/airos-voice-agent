"""Utilities for loading lecture metadata and content."""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Dict

import yaml

from .models import Lecture, LectureBranch


class LectureNotFoundError(KeyError):
    """Raised when a lecture identifier is unknown."""


class BranchNotFoundError(KeyError):
    """Raised when a requested branch is missing."""


class LectureStore:
    """Simple in-memory cache of lecture configurations."""

    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir
        self._lectures: Dict[str, Lecture] = {}
        self._lock = RLock()
        self._load_all()

    def _load_all(self) -> None:
        with self._lock:
            for path in sorted(self._config_dir.glob("lecture_*.yml")):
                with path.open("r", encoding="utf-8") as handle:
                    raw = yaml.safe_load(handle)
                lecture = Lecture.model_validate(raw)
                self._lectures[lecture.id] = lecture

    def get_lecture(self, lecture_id: str) -> Lecture:
        """Return the lecture data for ``lecture_id``."""

        try:
            return self._lectures[lecture_id]
        except KeyError as exc:  # pragma: no cover - simple mapping access
            raise LectureNotFoundError(lecture_id) from exc

    def get_branch(self, lecture_id: str, branch_id: str) -> LectureBranch:
        """Return branch content for the given lecture."""

        lecture = self.get_lecture(lecture_id)
        for branch in lecture.branches:
            if branch.id == branch_id:
                return branch
        raise BranchNotFoundError(branch_id)

    def list_lectures(self) -> list[Lecture]:
        """Return all available lectures."""

        return list(self._lectures.values())
