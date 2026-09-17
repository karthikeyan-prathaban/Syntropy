import logging
import re


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
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern, replacement in self.PATTERNS:
                msg = pattern.sub(replacement, msg)
            record.msg = msg
        return True


def apply_zero_leakage_logging() -> None:
    sanitizer = SensitiveDataSanitizerFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "app"):
        logging.getLogger(name).addFilter(sanitizer)
