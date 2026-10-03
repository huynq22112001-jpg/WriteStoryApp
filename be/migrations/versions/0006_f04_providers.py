"""Add providers, models, role assignments, and provider limits."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("protocol", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("secret_ref", sa.Text()),
        sa.Column("key_storage", sa.Text(), nullable=False),
        sa.Column("auto_discover", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("prefer_long_context", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("default_effort", sa.Text()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("discovery_status", sa.Text(), nullable=False, server_default="never"),
        sa.Column("discovery_error", sa.Text()),
        sa.Column("discovered_at", sa.Text()),
        sa.Column("discovery_attempted_at", sa.Text()),
        sa.Column("connection_status", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("connection_checked_at", sa.Text()),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "provider_models",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "provider_id",
            sa.Text(),
            sa.ForeignKey("providers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("discovery_rank", sa.Integer()),
        sa.Column("display_name", sa.Text()),
        sa.Column("max_input_tokens", sa.Integer()),
        sa.Column("max_tokens", sa.Integer()),
        sa.Column("supported_efforts_json", sa.Text()),
        sa.Column("capabilities_json", sa.Text()),
        sa.Column("price_input_per_mtok", sa.Float()),
        sa.Column("price_output_per_mtok", sa.Float()),
        sa.Column("price_cache_read_per_mtok", sa.Float()),
        sa.Column("price_cache_write_per_mtok", sa.Float()),
        sa.Column("allowed_roles_json", sa.Text()),
        sa.Column("max_concurrent_requests", sa.Integer()),
        sa.Column("long_context_variant_model_id", sa.Text()),
        sa.Column("long_context_params_json", sa.Text()),
        sa.Column("tokens_per_syllable", sa.Float()),
        sa.Column("user_edited_fields_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("first_seen_at", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.Text()),
        sa.Column("missing_since", sa.Text()),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("provider_id", "model_id"),
    )
    op.create_index("ix_provider_models_order", "provider_models", ["provider_id", "position"])
    op.create_table(
        "role_models",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE")),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.Text(), sa.ForeignKey("providers.id", ondelete="SET NULL")),
        sa.Column("model_id", sa.Text()),
        sa.Column("effort", sa.Text()),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "uq_role_models_app",
        "role_models",
        ["role"],
        unique=True,
        sqlite_where=sa.text("work_id IS NULL"),
    )
    op.create_index(
        "uq_role_models_work",
        "role_models",
        ["work_id", "role"],
        unique=True,
        sqlite_where=sa.text("work_id IS NOT NULL"),
    )
    op.create_table(
        "provider_limits",
        sa.Column(
            "provider_id",
            sa.Text(),
            sa.ForeignKey("providers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("max_concurrent_requests", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("rpm", sa.Integer()),
        sa.Column("tpm", sa.Integer()),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("cooldown_until", sa.Text()),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("provider_limits")
    op.drop_index("uq_role_models_work", table_name="role_models")
    op.drop_index("uq_role_models_app", table_name="role_models")
    op.drop_table("role_models")
    op.drop_index("ix_provider_models_order", table_name="provider_models")
    op.drop_table("provider_models")
    op.drop_table("providers")
