from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class VaultStatus(BaseModel):
    state: Literal["absent", "locked", "unlocked"]
    mode: Literal["undecided", "vault", "session_only"]
    kdf: Literal["argon2id", "scrypt"] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    waiting_jobs: int = 0
    throttle_ms: int = 0
    revision: int = Field(default=1, ge=1)


class CreateVaultRequest(BaseModel):
    password: SecretStr
    password_confirm: SecretStr
    import_session_secrets: bool = True


class UnlockRequest(BaseModel):
    password: SecretStr


class ChangePasswordRequest(BaseModel):
    current_password: SecretStr
    new_password: SecretStr
    new_password_confirm: SecretStr


class ResetVaultRequest(BaseModel):
    confirm: str


class VaultModeRequest(BaseModel):
    mode: Literal["vault", "session_only"]
    expected_revision: int = Field(ge=1)


class SecretInfo(BaseModel):
    ref: str
    storage: Literal["vault", "session"]
    available: bool
    label: str | None = None
    updated_at: str | None = None


class PutSecretRequest(BaseModel):
    value: SecretStr
    storage: Literal["vault", "session"]
    label: str | None = None
