import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class RedactFilter(logging.Filter):
    """Che token phiên/API key nếu vô tình xuất hiện trong log (Plan §3)."""

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = message
        for secret in self._secrets:
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
