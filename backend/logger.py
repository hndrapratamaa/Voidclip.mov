"""
backend/logger.py
─────────────────────────────────────────────────────────────────────────────
Voidclip.mov — Logging bootstrap

Call `setup_logging()` exactly once at application start (app.py does this).
All other modules obtain their logger via `get_logger(__name__)`.

Log files rotate daily and keep 7 days of history.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

# Imported lazily to avoid circular-import risk at module level
_LOGS_DIR: Path | None = None
_CONFIGURED = False

# ── Public API ─────────────────────────────────────────────────────────────

def setup_logging(
    level: int = logging.DEBUG,
    log_dir: Path | None = None,
) -> None:
    """
    Initialise root logger.  Safe to call multiple times — only the first
    call takes effect.
    """
    global _CONFIGURED, _LOGS_DIR

    if _CONFIGURED:
        return
    _CONFIGURED = True

    # Resolve log directory
    if log_dir is None:
        try:
            from backend.config import LOGS_DIR
            log_dir = LOGS_DIR
        except ImportError:
            log_dir = Path(__file__).resolve().parent.parent / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    _LOGS_DIR = log_dir

    root = logging.getLogger()
    root.setLevel(level)

    # Remove any handlers that may have been auto-added (e.g. by basicConfig)
    root.handlers.clear()

    # ── Console handler ───────────────────────────────────────────────────
    console_fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)-24s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(console_fmt)
    root.addHandler(ch)

    # ── Rotating file handler ─────────────────────────────────────────────
    file_fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "voidclip.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_fmt)
    root.addHandler(fh)

    # Silence overly verbose third-party loggers
    for noisy in ("PySide6", "PIL", "urllib3", "requests"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root.debug("Logging initialised — log dir: %s", log_dir)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named child logger.

    Usage::

        from backend.logger import get_logger
        log = get_logger(__name__)
        log.info("hello")
    """
    return logging.getLogger(name)
