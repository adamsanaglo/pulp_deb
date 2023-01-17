import logging

from app.core.config import settings

FORMAT = (
    "pmcserver %(asctime)s %(levelname)-7s [%(correlation_id)s]: %(name)s:%(lineno)d - %(message)s"
)
LEVEL = logging.DEBUG if settings.DEBUG else logging.INFO

DEFAULT_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation_id": {
            "()": "asgi_correlation_id.CorrelationIdFilter",
            "uuid_length": 32,
        },
    },
    "formatters": {
        "console": {
            "class": "logging.Formatter",
            "format": FORMAT,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["correlation_id"],
            "formatter": "console",
        },
    },
    "loggers": {
        # root logger
        "": {"handlers": ["console"], "level": LEVEL, "propagate": True},
        "uvicorn.access": {"level": logging.WARNING},
    },
}
