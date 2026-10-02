from __future__ import annotations

import asyncio
import base64
import json
import os
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag, UnsupportedAlgorithm
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

try:
    from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
except ImportError:  # Argon2id was added in cryptography 44; existing files still select by header.
    Argon2id = None

from writestory_be.core.ids import new_id

VAULT_FORMAT = "writestory-vault"
VAULT_VERSION = 1
CIPHER = "AES-256-GCM"
ARGON2ID_PARAMETERS = {
    "name": "argon2id",
    "memory_cost_kib": 19_456,
    "iterations": 2,
    "lanes": 1,
    "length": 32,
}
SCRYPT_PARAMETERS = {"name": "scrypt", "n": 2**17, "r": 8, "p": 1, "length": 32}


class VaultError(Exception):
    code = "VAULT_CORRUPT"

    def __init__(self, message: str, *, reason: str | None = None) -> None:
        self.reason = reason
        super().__init__(message)


class VaultPasswordInvalid(VaultError):
    code = "VAULT_PASSWORD_INVALID"


class VaultCorrupt(VaultError):
    code = "VAULT_CORRUPT"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64decode(value: str, *, expected_length: int | None = None) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise VaultCorrupt("Vault có dữ liệu base64 không hợp lệ") from exc
    if expected_length is not None and len(decoded) != expected_length:
        raise VaultCorrupt("Vault có trường mã hóa sai độ dài")
    return decoded


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _derive_key(
    password: str, salt: bytes, kdf: dict[str, Any] | None = None
) -> tuple[dict, bytes]:
    normalized = unicodedata.normalize("NFC", password).encode("utf-8")
    if kdf is None:
        if Argon2id is not None:
            try:
                params = dict(ARGON2ID_PARAMETERS)
                params.pop("name")
                params["memory_cost"] = params.pop("memory_cost_kib")
                key = Argon2id(salt=salt, **params).derive(normalized)
                return dict(ARGON2ID_PARAMETERS), key
            except UnsupportedAlgorithm:
                pass
        params = dict(SCRYPT_PARAMETERS)
        params.pop("name")
        return dict(SCRYPT_PARAMETERS), Scrypt(salt=salt, **params).derive(normalized)

    if kdf.get("name") == "argon2id":
        if Argon2id is None:
            raise VaultCorrupt("Bản backend không hỗ trợ Argon2id", reason="kdf_unsupported")
        try:
            key = Argon2id(
                salt=salt,
                length=int(kdf["length"]),
                iterations=int(kdf["iterations"]),
                lanes=int(kdf["lanes"]),
                memory_cost=int(kdf["memory_cost_kib"]),
            ).derive(normalized)
        except UnsupportedAlgorithm as exc:
            raise VaultCorrupt(
                "Bản backend không hỗ trợ Argon2id", reason="kdf_unsupported"
            ) from exc
        return dict(kdf), key
    if kdf.get("name") == "scrypt":
        try:
            key = Scrypt(
                salt=salt,
                length=int(kdf["length"]),
                n=int(kdf["n"]),
                r=int(kdf["r"]),
                p=int(kdf["p"]),
            ).derive(normalized)
        except (KeyError, TypeError, ValueError, UnsupportedAlgorithm) as exc:
            raise VaultCorrupt("Tham số Scrypt không hợp lệ") from exc
        return dict(kdf), key
    raise VaultCorrupt("Thuật toán dẫn xuất khóa không được hỗ trợ")


def _aad_fields(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": document["format"],
        "version": document["version"],
        "vault_id": document["vault_id"],
        "kdf": document["kdf"],
        "cipher": document["cipher"],
    }


def _decrypt_document(document: dict[str, Any], password: str) -> tuple[bytearray, dict[str, Any]]:
    try:
        if document["format"] != VAULT_FORMAT or document["version"] != VAULT_VERSION:
            raise VaultCorrupt("Định dạng vault không được hỗ trợ")
        if document["cipher"] != CIPHER or not isinstance(document["kdf"], dict):
            raise VaultCorrupt("Header vault không hợp lệ")
        salt = _b64decode(document["kdf"]["salt"], expected_length=16)
        kdf_parameters = {key: value for key, value in document["kdf"].items() if key != "salt"}
        _, key = _derive_key(password, salt, kdf_parameters)
        nonce = _b64decode(document["nonce"], expected_length=12)
        ciphertext = _b64decode(document["ciphertext"])
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, _canonical_json(_aad_fields(document)))
        decoded = json.loads(plaintext)
        if decoded.get("v") != 1 or not isinstance(decoded.get("entries"), dict):
            raise VaultCorrupt("Nội dung vault không hợp lệ")
        return bytearray(key), decoded["entries"]
    except InvalidTag as exc:
        raise VaultPasswordInvalid("Mật khẩu không đúng hoặc vault đã bị sửa") from exc
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, VaultError):
            raise
        raise VaultCorrupt("File vault bị hỏng") from exc


def _with_salt(document: dict[str, Any], salt: bytes) -> dict[str, Any]:
    result = dict(document)
    result["kdf"] = {**result["kdf"], "salt": _b64encode(salt)}
    return result


class VaultFile:
    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        return self.path.is_file()

    def read(self) -> dict[str, Any]:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("Expected object")
            return document
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise VaultCorrupt("Không thể đọc file vault") from exc

    def write(self, document: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(self.path.name + ".tmp")
        payload = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        try:
            with temp_path.open("w", encoding="utf-8", newline="\n") as file:
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())
            if os.name != "nt":
                os.chmod(temp_path, 0o600)
            os.replace(temp_path, self.path)
            if os.name != "nt":
                directory_fd = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            temp_path.unlink(missing_ok=True)


class VaultService:
    def __init__(self, path: Path) -> None:
        self.file = VaultFile(path)
        self._key: bytearray | None = None
        self._entries: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        if self._key is not None:
            return "unlocked"
        return "locked" if self.file.exists() else "absent"

    async def create(self, password: str, password_confirm: str) -> str:
        password = unicodedata.normalize("NFC", password)
        password_confirm = unicodedata.normalize("NFC", password_confirm)
        if password != password_confirm:
            raise ValueError("Mật khẩu xác nhận không khớp")
        if len(password) < 8:
            raise ValueError("Mật khẩu cần ít nhất 8 ký tự")
        async with self._lock:
            if self.file.exists():
                raise FileExistsError("Vault đã tồn tại")
            document, salt = await asyncio.to_thread(self._create_document, password)
            self.file.write(document)
            self._key, self._entries = await asyncio.to_thread(
                self._decrypt_with_salt, document, password, salt
            )
            return document["vault_id"]

    @staticmethod
    def _create_document(password: str) -> tuple[dict[str, Any], bytes]:
        salt = os.urandom(16)
        document, salt = _encrypt_with_salt(password, {}, new_id(), salt)
        return document, salt

    @staticmethod
    def _decrypt_with_salt(
        document: dict[str, Any], password: str, _salt: bytes
    ) -> tuple[bytearray, dict[str, Any]]:
        return _decrypt_document(document, password)

    async def unlock(self, password: str) -> None:
        async with self._lock:
            document = await asyncio.to_thread(self.file.read)
            key, entries = await asyncio.to_thread(_decrypt_document, document, password)
            self._key, self._entries = key, entries

    async def lock(self) -> None:
        async with self._lock:
            if self._key is not None:
                self._key[:] = b"\0" * len(self._key)
            self._key = None
            self._entries.clear()

    async def change_password(
        self, current_password: str, new_password: str, confirmation: str
    ) -> None:
        new_password = unicodedata.normalize("NFC", new_password)
        confirmation = unicodedata.normalize("NFC", confirmation)
        if new_password != confirmation:
            raise ValueError("Mật khẩu xác nhận không khớp")
        if len(new_password) < 8:
            raise ValueError("Mật khẩu cần ít nhất 8 ký tự")
        async with self._lock:
            document = await asyncio.to_thread(self.file.read)
            old_key, entries = await asyncio.to_thread(
                _decrypt_document, document, current_password
            )
            old_key[:] = b"\0" * len(old_key)
            updated, salt = await asyncio.to_thread(
                _encrypt_with_salt,
                new_password,
                entries,
                document["vault_id"],
                os.urandom(16),
                document,
            )
            self.file.write(updated)
            if self._key is not None:
                self._key[:] = b"\0" * len(self._key)
            self._key, self._entries = await asyncio.to_thread(
                self._decrypt_with_salt, updated, new_password, salt
            )

    async def put(self, ref: str, value: str, label: str | None = None) -> None:
        async with self._lock:
            if self._key is None:
                raise PermissionError("Vault đang khóa")
            entries = dict(self._entries)
            entries[ref] = {"value": value, "label": label, "updated_at": _now()}
            document = await asyncio.to_thread(
                _encrypt_with_key, self.file.read(), entries, self._key
            )
            await asyncio.to_thread(self.file.write, document)
            self._entries = entries

    async def get(self, ref: str) -> dict[str, Any] | None:
        async with self._lock:
            if self._key is None:
                raise PermissionError("Vault đang khóa")
            return self._entries.get(ref)

    async def refs(self) -> tuple[str, ...]:
        async with self._lock:
            if self._key is None:
                raise PermissionError("Vault đang khóa")
            return tuple(self._entries)

    async def delete(self, ref: str) -> None:
        async with self._lock:
            if self._key is None:
                raise PermissionError("Vault đang khóa")
            if ref not in self._entries:
                return
            entries = dict(self._entries)
            del entries[ref]
            document = await asyncio.to_thread(
                _encrypt_with_key, self.file.read(), entries, self._key
            )
            await asyncio.to_thread(self.file.write, document)
            self._entries = entries


def _encrypt_with_salt(
    password: str,
    entries: dict[str, Any],
    vault_id: str,
    salt: bytes,
    previous: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bytes]:
    kdf, key = _derive_key(password, salt)
    now = _now()
    document: dict[str, Any] = {
        "format": VAULT_FORMAT,
        "version": VAULT_VERSION,
        "vault_id": vault_id or new_id(),
        "kdf": {**kdf, "salt": _b64encode(salt)},
        "cipher": CIPHER,
        "nonce": "",
        "ciphertext": "",
        "created_at": previous.get("created_at", now) if previous else now,
        "updated_at": now,
    }
    nonce = os.urandom(12)
    plaintext = _canonical_json({"v": 1, "entries": entries})
    aad = _canonical_json(_aad_fields(document))
    document["nonce"] = _b64encode(nonce)
    document["ciphertext"] = _b64encode(AESGCM(key).encrypt(nonce, plaintext, aad))
    return document, salt


def _encrypt_with_key(
    previous: dict[str, Any], entries: dict[str, Any], key: bytearray
) -> dict[str, Any]:
    document = dict(previous)
    document["updated_at"] = _now()
    nonce = os.urandom(12)
    plaintext = _canonical_json({"v": 1, "entries": entries})
    document["nonce"] = _b64encode(nonce)
    document["ciphertext"] = _b64encode(
        AESGCM(bytes(key)).encrypt(nonce, plaintext, _canonical_json(_aad_fields(document)))
    )
    return document
