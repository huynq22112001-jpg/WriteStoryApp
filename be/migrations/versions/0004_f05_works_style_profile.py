"""Create projects, works, and style_profile for F05.

Revision ID: 0004
Revises: 0003
"""

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "works",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Text(),
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("title_search", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False, server_default="vi"),
        sa.Column("genre", sa.Text()),
        sa.Column("genre_label_custom", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("brief", sa.Text()),
        sa.Column("target_chapters", sa.Integer()),
        sa.Column("chapter_length_min", sa.Integer(), nullable=False, server_default="2500"),
        sa.Column("chapter_length_max", sa.Integer(), nullable=False, server_default="3500"),
        sa.Column("autowrite_mode_default", sa.Text(), nullable=False, server_default="auto"),
        sa.Column("review_every_k", sa.Integer()),
        sa.Column("max_repair_rounds", sa.Integer()),
        sa.Column("budget_daily_usd", sa.Float()),
        sa.Column("budget_daily_tokens", sa.Integer()),
        sa.Column("continuity_status", sa.Text(), nullable=False, server_default="ok"),
        sa.Column("continuity_chapter_no", sa.Integer()),
        sa.Column("continuity_reason", sa.Text()),
        sa.Column("cover_asset_id", sa.Text(), sa.ForeignKey("assets.id", ondelete="SET NULL")),
        sa.Column("wizard_step", sa.Text()),
        sa.Column("wizard_completed_steps", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("last_opened_at", sa.Text()),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.Text()),
        sa.CheckConstraint("language = 'vi'", name="ck_works_language_vi"),
        sa.CheckConstraint("status IN ('draft','ready','archived')", name="ck_works_status_valid"),
        sa.CheckConstraint(
            "continuity_status IN ('ok','blocked_needs_resync','stale_from')",
            name="ck_works_continuity_status_valid",
        ),
        sa.CheckConstraint(
            "autowrite_mode_default IN ('auto','review_each','review_every_k')",
            name="ck_works_autowrite_mode_valid",
        ),
        sa.CheckConstraint(
            "chapter_length_min < chapter_length_max", name="ck_works_chapter_length_valid"
        ),
        sa.CheckConstraint(
            "(continuity_status = 'stale_from' AND continuity_chapter_no IS NOT NULL "
            "AND continuity_reason IS NOT NULL) OR (continuity_status != 'stale_from' "
            "AND continuity_chapter_no IS NULL AND continuity_reason IS NULL)",
            name="ck_works_continuity_stale_fields",
        ),
        sa.CheckConstraint(
            "autowrite_mode_default != 'review_every_k' OR review_every_k IS NOT NULL",
            name="ck_works_review_every_k_required",
        ),
    )
    op.create_index("ix_works_deleted_updated", "works", ["deleted_at", "updated_at"])
    op.create_index("ix_works_status", "works", ["status"])
    op.create_index("ix_works_genre", "works", ["genre"])
    op.create_index("ix_works_last_opened", "works", ["last_opened_at"])
    op.create_index("ix_works_project_id", "works", ["project_id"])
    op.create_table(
        "style_profile",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id",
            sa.Text(),
            sa.ForeignKey("works.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("vocab_register", sa.Text(), nullable=False),
        sa.Column("dialogue_style", sa.Text(), nullable=False),
        sa.Column("dialogue_dash_char", sa.Text()),
        sa.Column("tone_mark_style", sa.Text(), nullable=False),
        sa.Column("punctuation_rules", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("banned_phrases", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("voice", sa.Text()),
        sa.Column("voice_samples", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "vocab_register IN ('han_viet','balanced','thuan_viet')",
            name="ck_style_profile_vocab_valid",
        ),
        sa.CheckConstraint(
            "dialogue_style IN ('dash','quotes')", name="ck_style_profile_dialogue_valid"
        ),
        sa.CheckConstraint(
            "tone_mark_style IN ('old','new')", name="ck_style_profile_tone_mark_valid"
        ),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text("INSERT INTO projects(id, name, created_at) VALUES (:id, :name, :created_at)"),
        {
            "id": str(uuid.uuid7()),
            "name": "Mặc định",
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )


def downgrade() -> None:
    op.drop_table("style_profile")
    op.drop_index("ix_works_project_id", table_name="works")
    op.drop_index("ix_works_last_opened", table_name="works")
    op.drop_index("ix_works_genre", table_name="works")
    op.drop_index("ix_works_status", table_name="works")
    op.drop_index("ix_works_deleted_updated", table_name="works")
    op.drop_table("works")
    op.drop_table("projects")
