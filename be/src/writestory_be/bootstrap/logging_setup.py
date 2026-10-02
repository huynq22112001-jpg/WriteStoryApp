import logging
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

_secret_values: set[str] = set()
_secret_values_lock = threading.Lock()


def register_secret(value: str) -> None:
    if value:
        with _secret_values_lock:
            _secret_values.add(value)


class RedactFilter(logging.Filter):
    """Che token phiên/API key nếu vô tình xuất hiện trong log (Plan §3)."""

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        for secret in secrets:
            register_secret(secret)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = message
        with _secret_values_lock:
            secrets = tuple(_secret_values)
        for secret in secrets:
            redacted = redacted.replace(secret, "***")
        if redacted != message:
            record.msg, record.args = redacted, None
        return True


def configure_logging(logs_dir: Path, level: str, secrets: list[str]) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    redact = RedactFilter(secrets)

    file_handler = RotatingFileHandler(
        logs_dir / "backend.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    stderr_handler = logging.StreamHandler()
    for handler in (file_handler, stderr_handler):
        handler.setFormatter(formatter)
        handler.addFilter(redact)

    root = logging.getLogger()
    root.handlers[:] = [file_handler, stderr_handler]
    root.setLevel(level.upper())
