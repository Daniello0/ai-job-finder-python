"""Python entrypoint for launching backend FastAPI server."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

from common.constants.api import (
    API_HOST_ENV,
    API_PORT_ENV,
    API_RELOAD_ENV,
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
    DEFAULT_API_RELOAD,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _to_bool(value: str | None, default: bool) -> bool:
    """Convert env value to bool with fallback default."""

    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _server_config() -> tuple[str, int, bool]:
    """Read host/port/reload configuration from env variables."""

    host = os.getenv(API_HOST_ENV, DEFAULT_API_HOST)
    port = int(os.getenv(API_PORT_ENV, str(DEFAULT_API_PORT)))
    reload_enabled = _to_bool(os.getenv(API_RELOAD_ENV), DEFAULT_API_RELOAD)
    return host, port, reload_enabled


def main() -> None:
    """Run FastAPI app so `python backend/src/main.py` starts the server."""

    load_dotenv(BACKEND_DIR / ".env")
    host, port, reload_enabled = _server_config()
    uvicorn.run("api:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
