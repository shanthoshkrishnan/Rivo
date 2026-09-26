"""
RIVO Backend — Structured Logging Setup
========================================
Configures Loguru as the application-wide logger.
Every log record includes:
  - timestamp (ISO-8601 with timezone)
  - log level
  - module + function + line
  - message

Usage:
    from app.core.logging import logger
    logger.info("Rental provider loaded", provider="mock")
"""
from __future__ import annotations

import sys
from app.core.config import get_settings
from loguru import logger


def configure_logging() -> None:
    """
    Remove Loguru defaults and install a production-friendly handler.
    Call once from the FastAPI lifespan startup handler.
    """
    settings = get_settings()
    logger.remove()  # Remove default stderr handler

    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS Z}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=fmt,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=settings.APP_ENV != "production",
    )

    # File sink for persistent logs (rotate daily, keep 14 days)
    logger.add(
        "logs/rivo_{time:YYYY-MM-DD}.log",
        format=fmt,
        level="DEBUG",
        rotation="00:00",
        retention="14 days",
        compression="gz",
        enqueue=True,   # async-safe
    )

    logger.info(
        "RIVO logging initialised",
        env=settings.APP_ENV,
        level=settings.LOG_LEVEL,
    )


__all__ = ["logger", "configure_logging"]
