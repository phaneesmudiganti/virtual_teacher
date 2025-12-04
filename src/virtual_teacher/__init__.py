import logging
import logging.handlers
from pathlib import Path
import os

def _configure_default_logging():
    root = logging.getLogger()
    if root.handlers:
        return
    log_dir = Path.cwd() / "logs"
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        pass
    stream_handler = logging.StreamHandler()
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_dir / "virtual_teacher.log"), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[stream_handler, file_handler]
    )

_configure_default_logging()
