"""Create chapters and immutable chapter revisions."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chapters",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("state_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_revision_id", sa.Text()),
        sa.Column("revision_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("syllable_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.Text()),
        sa.CheckConstraint(
            "status IN ('draft','drafting','checking','revising','waiting_user','committed')",
            name="ck_chapters_status_valid",
        ),
    )
    op.create_index(
        "uq_chapters_work_no_active",
        "chapters",
        ["work_id", "chapter_no"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_chapters_work_no", "chapters", ["work_id", "chapter_no"])
    op.create_table(
        "chapter_revisions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "chapter_id",
            sa.Text(),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("parent_revision_id", sa.Text()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("doc_json", sa.Text(), nullable=False),
        sa.Column("plain_text", sa.Text(), nullable=False),
        sa.Column("paragraphs_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("syllable_count", sa.Integer(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("restored_from_revision_id", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("chapter_id", "revision_no"),
    )
    op.create_index(
        "ix_chapter_revisions_created", "chapter_revisions", ["chapter_id", "created_at"]
    )
    op.create_table(
        "chapter_working_copy",
        sa.Column(
            "chapter_id",
            sa.Text(),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("base_revision_id", sa.Text()),
        sa.Column("doc_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("has_changes", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("client_session_id", sa.Text()),
        sa.Column("client_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("chapter_working_copy")
    op.drop_index("ix_chapter_revisions_created", table_name="chapter_revisions")
    op.drop_table("chapter_revisions")
    op.drop_index("ix_chapters_work_no", table_name="chapters")
    op.drop_index("uq_chapters_work_no_active", table_name="chapters")
    op.drop_table("chapters")
