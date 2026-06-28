"""Frontend logging for crashes and API failures."""

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "hrms-client.log"
ERROR_LOG_FILE = LOG_DIR / "hrms-client-error.log"

_FORMAT = logging.Formatter(
    "%(levelname)s %(asctime)s %(name)s %(message)s"
)


def setup_logging():
    """Configure rotating log files for the desktop client."""

    root = logging.getLogger("hrms.client")
    if root.handlers:
        return root

    root.setLevel(logging.INFO)

    for path, level in ((LOG_FILE, logging.INFO), (ERROR_LOG_FILE, logging.ERROR)):
        handler = RotatingFileHandler(
            path,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(_FORMAT)
        root.addHandler(handler)

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(_FORMAT)
    root.addHandler(console)

    return root


def install_exception_hook(logger=None):
    """Log uncaught exceptions instead of crashing silently."""

    log = logger or setup_logging()
    original_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        if exc_type is KeyboardInterrupt:
            original_hook(exc_type, exc_value, exc_tb)
            return
        log.critical(
            "Uncaught exception:\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        original_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook
