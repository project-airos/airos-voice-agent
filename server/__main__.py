"""Entrypoint for running the lecture demo server with ``python -m``."""

from __future__ import annotations

import uvicorn

from .config import get_settings
from .main import create_app


def main() -> None:
    settings = get_settings()
    app = create_app(settings)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
