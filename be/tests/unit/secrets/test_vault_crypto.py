import json

import pytest

from writestory_be.infrastructure.secrets import vault
from writestory_be.infrastructure.secrets.vault import (
    VaultCorrupt,
    VaultPasswordInvalid,
    VaultService,
)


@pytest.mark.asyncio
async def test_vault_round_trip_password_change_lock_and_no_plaintext_on_disk(tmp_path) -> None:
    secret = "sk-live-super-secret"
    path = tmp_path / "secrets.enc"
    service = VaultService(path)
    await service.create("mat khau ban dau", "mat khau ban dau")
    await service.put("provider:p1:api_key", secret, "OpenAI")
    first_document = json.loads(path.read_text(encoding="utf-8"))
    await service.put("provider:p1:api_key", secret, "OpenAI")
    second_document = json.loads(path.read_text(encoding="utf-8"))

    assert first_document["nonce"] != second_document["nonce"]
    assert secret not in path.read_text(encoding="utf-8")
    on_disk = "".join(
        item.read_text(encoding="utf-8", errors="ignore")
        for item in tmp_path.iterdir()
        if item.is_file()
    )
    assert secret not in on_disk

    await service.lock()
    reopened = VaultService(path)
    with pytest.raises(VaultPasswordInvalid):
        await reopened.unlock("sai mat khau")
    await reopened.unlock("mat khau ban dau")
    assert (await reopened.get("provider:p1:api_key"))["value"] == secret
    await reopened.change_password("mat khau ban dau", "mat khau moi", "mat khau moi")
    await reopened.lock()
    with pytest.raises(VaultPasswordInvalid):
        await reopened.unlock("mat khau ban dau")
    await reopened.unlock("mat khau moi")
    assert (await reopened.get("provider:p1:api_key"))["value"] == secret


@pytest.mark.asyncio
async def test_malformed_vault_file_is_reported_as_corrupt(tmp_path) -> None:
    path = tmp_path / "secrets.enc"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(VaultCorrupt):
        await VaultService(path).unlock("password")


def test_argon2id_unsupported_uses_scrypt_fallback(monkeypatch) -> None:
    class UnsupportedArgon2id:
        def __init__(self, **_kwargs):
            raise vault.UnsupportedAlgorithm("not available")

    class FakeScrypt:
        def __init__(self, **kwargs):
            self.parameters = kwargs

        def derive(self, _password):
            return b"k" * 32

    monkeypatch.setattr(vault, "Argon2id", UnsupportedArgon2id)
    monkeypatch.setattr(vault, "Scrypt", FakeScrypt)
    kdf, key = vault._derive_key("password", b"s" * 16)
    assert kdf["name"] == "scrypt"
    assert kdf["n"] == 2**17 and kdf["r"] == 8 and kdf["p"] == 1
    assert key == b"k" * 32
