import logging

import pytest

from writestory_be.bootstrap.logging_setup import RedactFilter
from writestory_be.infrastructure.secrets.redaction import SecretRedactor
from writestory_be.infrastructure.secrets.secret_store import SecretStore
from writestory_be.infrastructure.secrets.session_store import SessionSecretStore
from writestory_be.infrastructure.secrets.vault import VaultService


@pytest.mark.asyncio
async def test_session_secrets_are_process_local(tmp_path) -> None:
    path = tmp_path / "secrets.enc"
    first_session = SessionSecretStore()
    first = SecretStore(VaultService(path), first_session)
    await first.put("provider:one:api_key", "session-only-key", "session")

    restarted = SecretStore(VaultService(path), SessionSecretStore())
    assert await restarted.availability("provider:one:api_key") == "missing"


def test_secret_registered_after_logging_setup_is_redacted() -> None:
    redactor = SecretRedactor()
    redactor.add("sk-session-secret")
    record = logging.LogRecord(
        "test", logging.INFO, __file__, 1, "key=%s", ("sk-session-secret",), None
    )

    assert RedactFilter([]).filter(record)
    assert record.getMessage() == "key=***"

