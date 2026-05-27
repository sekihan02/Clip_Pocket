from __future__ import annotations

import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from clip_pocket.constants import APP_NAME


def log_file_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        root = Path(base)
    else:
        root = Path.home() / "AppData" / "Local"
    return root / "ClipPocket" / "logs" / "clip-pocket.log"


def configure_logging() -> Path:
    path = log_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=512_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True,
    )
    logging.info("Starting %s", APP_NAME)
    return path


def show_startup_error(exc: BaseException) -> None:
    message = (
        f"{APP_NAME} failed to start.\n\n"
        f"{exc}\n\n"
        f"Log: {log_file_path()}"
    )

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
            return
        except Exception:
            pass

    print(message, file=sys.stderr)
    traceback.print_exception(exc, file=sys.stderr)
