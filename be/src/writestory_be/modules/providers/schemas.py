import re
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, SecretStr, field_validator

Protocol = Literal["anthropic", "openai_compatible", "ollama_lmstudio"]
Role = Literal["planner", "writer", "checker", "reviewer", "summary"]


def clean_url(value: str) -> str:
    from urllib.parse import urlsplit

    value = value.strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url_must_be_http")
    return value


class ProviderIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    protocol: Protocol
    base_url: str = Field(min_length=1, max_length=500)
    api_key: SecretStr | None = None
    key_storage: Literal["vault", "session", "none"] = "none"
    auto_discover: bool = True
    prefer_long_context: bool = False
    default_effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None
    enabled: bool = True

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        return clean_url(value)


class ProviderPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = None
    api_key: SecretStr | None = None
    key_storage: Literal["vault", "session", "none"] | None = None
    auto_discover: bool | None = None
    prefer_long_context: bool | None = None
    default_effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None
    enabled: bool | None = None

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value: str | None) -> str | None:
        return clean_url(value) if value is not None else value


class ModelItem(BaseModel):
    model_id: str = Field(min_length=1, max_length=300)
    display_name: str | None = None
    max_input_tokens: int | None = Field(default=None, ge=1)
    max_tokens: int | None = Field(default=None, ge=1)
    supported_efforts: list[str] | None = None
    price_input_per_mtok: float | None = Field(default=None, ge=0)
    price_output_per_mtok: float | None = Field(default=None, ge=0)
    price_cache_read_per_mtok: float | None = Field(default=None, ge=0)
    price_cache_write_per_mtok: float | None = Field(default=None, ge=0)
    allowed_roles: list[Role] | None = None
    max_concurrent_requests: int | None = Field(default=None, ge=1)
    long_context_variant_model_id: str | None = None
    long_context_params: dict[str, Any] | None = None
    tokens_per_syllable: float | None = Field(default=None, gt=0)
    reset_fields: list[str] = Field(default_factory=list)


class ModelsPut(BaseModel):
    expected_revision: int = Field(ge=1)
    items: list[ModelItem]


class RoleAssignment(BaseModel):
    role: Role
    provider_id: str | None = None
    model_id: str | None = None
    effort: str | None = None


class RolesPut(BaseModel):
    roles: list[RoleAssignment]


class LimitsIn(BaseModel):
    max_concurrent_requests: int = Field(ge=1, le=128)
    rpm: int | None = Field(default=None, ge=1)
    tpm: int | None = Field(default=None, ge=1)
    max_retries: int = Field(default=3, ge=0, le=10)


class AppLimitsIn(BaseModel):
    worker_pool: int = Field(default=4, ge=1, le=64)
    app_daily_usd: float | None = Field(default=None, ge=0)
    app_daily_tokens: int | None = Field(default=None, ge=0)
    work_daily_usd_default: float | None = Field(default=None, ge=0)
    timezone: str = "Asia/Bangkok"
    autowrite_mode_default: Literal["auto", "review_each", "review_every_k"] = "review_each"
    review_every_k: int = Field(default=5, ge=1, le=100)
    max_repair_rounds: int = Field(default=2, ge=0, le=10)
    chapter_length_min: int = Field(default=1500, ge=1)
    chapter_length_max: int = Field(default=2500, ge=1)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            # Windows installations may not ship the IANA database; keep its
            # canonical region/city syntax valid while rejecting arbitrary text.
            if value != "UTC" and not re.fullmatch(r"[A-Za-z_+-]+(?:/[A-Za-z0-9_+-]+)+", value):
                raise ValueError("timezone_must_be_iana") from exc
        return value

    @field_validator("chapter_length_max")
    @classmethod
    def max_length_after_min(cls, value: int, info) -> int:
        if value < info.data.get("chapter_length_min", value):
            raise ValueError("chapter_length_range_invalid")
        return value


class ProviderTestIn(BaseModel):
    provider_id: str | None = None
    protocol: Protocol | None = None
    base_url: str | None = None
    api_key: SecretStr | None = None
    model_id: str | None = None
