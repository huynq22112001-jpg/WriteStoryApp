"""Normalized provider model metadata exposed by discovery adapters."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from writestory_ai.contracts.generation import Effort


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    display_name: str | None = None
    max_input_tokens: int | None = Field(default=None, ge=1)
    max_tokens: int | None = Field(default=None, ge=1)
    supported_efforts: list[Effort] | None = None
    capabilities: dict[str, Any] | None = None
