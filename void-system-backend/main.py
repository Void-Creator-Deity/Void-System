"""Void System backend entry point."""
from __future__ import annotations

import logging
from pathlib import Path

import uvicorn
from dotenv import load_dotenv


_BACKEND_ROOT = Path(__file__).resolve().parent
_ENV_FILE = _BACKEND_ROOT / ".env"
load_dotenv(_ENV_FILE)

from api.http.application import create_app
from config import Config


logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        log_level=Config.LOG_LEVEL.lower(),
        reload=Config.RELOAD,
        reload_excludes=["**/data/**", "**/session_temp/**", "**/__pycache__/**", "**/.git/**"],
    )
