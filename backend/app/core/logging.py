import logging
import re
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")


class SensitiveDataSanitizerFilter(logging.Filter):
    PATTERNS = [
        (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_\.=]+", re.IGNORECASE), r"\1[REDACTED_JWT]"),
        (
            re.compile(
                r"(['\"]?(?:client_secret|token|password|secret|key)['\"]?\s*[:=]\s*['\"])[^'\"}\s]+(['\"])",
                re.IGNORECASE,
            ),
            r"\1[REDACTED]\2",
        ),
        (re.compile(r"(otp\s*[:=]\s*['\"]?)(\d{6})(['\"]?)", re.IGNORECASE), r"\1[REDACTED_OTP]\3"),
        # Bare account numbers and card PANs must never reach a log aggregator.
        (re.compile(r"\b\d{12,19}\b"), "[REDACTED_ACCOUNT]"),
        (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern, replacement in self.PATTERNS:
                msg = pattern.sub(replacement, msg)
            record.msg = msg
        return True


class ContextFilter(logging.Filter):
    """Attach the current request and user to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True


def _json_handler() -> logging.Handler:
    from pythonjsonlogger import jsonlogger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(request_id)s %(user_id)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    )
    return handler


def configure_logging() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()

    if settings.is_production:
        handler: logging.Handler = _json_handler()
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s")
        )

    handler.addFilter(ContextFilter())
    handler.addFilter(SensitiveDataSanitizerFilter())
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "app", "arq"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

    # SQLAlchemy echoes bound parameters, which include encrypted PII.
    logging.getLogger("sqlalchemy.engine").setLevel("WARNING")


def apply_zero_leakage_logging() -> None:
    """Backwards-compatible entry point."""
    configure_logging()
