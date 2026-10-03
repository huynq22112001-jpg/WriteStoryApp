from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from writestory_be.infrastructure.db.base import Base


class Provider(Base):
    __tablename__ = "providers"
    __table_args__ = (UniqueConstraint("name"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    protocol: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    secret_ref: Mapped[str | None] = mapped_column(Text)
    key_storage: Mapped[str] = mapped_column(Text, nullable=False, default="none")
    auto_discover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prefer_long_context: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_effort: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    discovery_status: Mapped[str] = mapped_column(Text, nullable=False, default="never")
    discovery_error: Mapped[str | None] = mapped_column(Text)
    discovered_at: Mapped[str | None] = mapped_column(Text)
    discovery_attempted_at: Mapped[str | None] = mapped_column(Text)
    connection_status: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    connection_checked_at: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderModel(Base):
    __tablename__ = "provider_models"
    __table_args__ = (
        UniqueConstraint("provider_id", "model_id"),
        Index("ix_provider_models_order", "provider_id", "position"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        Text, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    discovery_rank: Mapped[int | None] = mapped_column(Integer)
    display_name: Mapped[str | None] = mapped_column(Text)
    max_input_tokens: Mapped[int | None] = mapped_column(Integer)
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    supported_efforts_json: Mapped[str | None] = mapped_column(Text)
    capabilities_json: Mapped[str | None] = mapped_column(Text)
    price_input_per_mtok: Mapped[float | None] = mapped_column()
    price_output_per_mtok: Mapped[float | None] = mapped_column()
    price_cache_read_per_mtok: Mapped[float | None] = mapped_column()
    price_cache_write_per_mtok: Mapped[float | None] = mapped_column()
    allowed_roles_json: Mapped[str | None] = mapped_column(Text)
    max_concurrent_requests: Mapped[int | None] = mapped_column(Integer)
    long_context_variant_model_id: Mapped[str | None] = mapped_column(Text)
    long_context_params_json: Mapped[str | None] = mapped_column(Text)
    tokens_per_syllable: Mapped[float | None] = mapped_column()
    user_edited_fields_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    first_seen_at: Mapped[str] = mapped_column(Text, nullable=False)
    last_seen_at: Mapped[str | None] = mapped_column(Text)
    missing_since: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class RoleModel(Base):
    __tablename__ = "role_models"
    __table_args__ = (
        Index("uq_role_models_app", "role", unique=True, sqlite_where=text("work_id IS NULL")),
        Index(
            "uq_role_models_work",
            "work_id",
            "role",
            unique=True,
            sqlite_where=text("work_id IS NOT NULL"),
        ),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str | None] = mapped_column(Text, ForeignKey("works.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("providers.id", ondelete="SET NULL")
    )
    model_id: Mapped[str | None] = mapped_column(Text)
    effort: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderLimit(Base):
    __tablename__ = "provider_limits"
    provider_id: Mapped[str] = mapped_column(
        Text, ForeignKey("providers.id", ondelete="CASCADE"), primary_key=True
    )
    max_concurrent_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    rpm: Mapped[int | None] = mapped_column(Integer)
    tpm: Mapped[int | None] = mapped_column(Integer)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    cooldown_until: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
