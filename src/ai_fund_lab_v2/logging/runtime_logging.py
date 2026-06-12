from __future__ import annotations

import logging
from pathlib import Path


def configure_runtime_logger(name: str, log_dir: Path, filename: str | None = None) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_file = log_dir / (filename or f"{name.replace('.', '_')}.log")
    if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_file for handler in logger.handlers):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)

    return logger
