"""Logging configuration for the GUI application."""

from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


def _get_log_dir() -> Path:
    """Return the log directory path."""
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    log_dir = Path(local_app_data) / "umu-advanced" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _get_log_path() -> Path:
    """Return the log file path with date suffix."""
    log_dir = _get_log_dir()
    today = datetime.now().strftime("%Y%m%d")
    return log_dir / f"app_{today}.log"


def setup_logging() -> None:
    """Configure file and console logging."""
    log_path = _get_log_path()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8", mode="a"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized. Log file: %s", log_path)


def get_log_dir() -> Path:
    """Return the log directory for external use."""
    return _get_log_dir()


def setup_excepthook() -> None:
    """Install a global exception hook to log uncaught exceptions."""
    original_hook = sys.excepthook

    def _excepthook(exc_type, exc_value, exc_tb):
        logger = logging.getLogger("uncaught")
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical("Uncaught exception:\n%s", tb_str)
        original_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook
