"""Runtime configuration helpers for the lecture demo server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    """Application configuration values."""

    version: str = "0.1.0"
    ws_url_template: str = "ws://localhost:8000/ws/{session_id}"
    dataflow_path: str = "core/dataflow-hybrid.yml"
    lecture_config_dir: str = "configs"

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables with sensible defaults."""

        return cls(
            version=os.getenv("AIROS_SERVER_VERSION", "0.1.0"),
            ws_url_template=os.getenv(
                "AIROS_WS_URL_TEMPLATE", "ws://localhost:8000/ws/{session_id}"
            ),
            dataflow_path=os.getenv("AIROS_DATAFLOW_PATH", "core/dataflow-hybrid.yml"),
            lecture_config_dir=os.getenv("AIROS_LECTURE_CONFIG_DIR", "configs"),
        )


def get_settings() -> Settings:
    """Return a singleton settings object."""

    if not hasattr(get_settings, "_settings"):
        get_settings._settings = Settings.from_env()
    return get_settings._settings  # type: ignore[attr-defined]
