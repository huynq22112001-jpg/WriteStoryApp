"""Add canonical story state, ledger, summaries, traces, and pending deltas."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chapters", sa.Column("state_id", sa.Text()))
    op.create_table(
        "story_states",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column(
            "revision_id", sa.Text(), sa.ForeignKey("chapter_revisions.id", ondelete="SET NULL")
        ),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("state_hash", sa.Text(), nullable=False),
        sa.Column("delta_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "parent_state_id", sa.Text(), sa.ForeignKey("story_states.id", ondelete="SET NULL")
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("job_id", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint("chapter_no >= 0", name="chapter_no_nonnegative"),
        sa.CheckConstraint(
            "source IN ('seed','pipeline','user_edit','resync')", name="source_valid"
        ),
    )
    op.create_index(
        "uq_story_states_current",
        "story_states",
        ["work_id", "chapter_no"],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
    )
    op.create_index("ix_story_states_work_chapter", "story_states", ["work_id", "chapter_no"])
    op.create_table(
        "facts",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("subject_ref", sa.Text()),
        sa.Column("predicate", sa.Text(), nullable=False),
        sa.Column("object", sa.Text(), nullable=False),
        sa.Column("valid_from_chapter", sa.Integer(), nullable=False),
        sa.Column("valid_until_chapter", sa.Integer()),
        sa.Column("source_chapter", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column(
            "created_state_id", sa.Text(), sa.ForeignKey("story_states.id", ondelete="SET NULL")
        ),
        sa.Column(
            "closed_state_id", sa.Text(), sa.ForeignKey("story_states.id", ondelete="SET NULL")
        ),
        sa.CheckConstraint("status IN ('active','closed','retracted')", name="status_valid"),
    )
    op.create_index("ix_facts_work_status", "facts", ["work_id", "status"])
    op.create_table(
        "hooks",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("opened_at_chapter", sa.Integer(), nullable=False),
        sa.Column("due_by_chapter", sa.Integer()),
        sa.Column("payoff_plan", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("last_advanced_chapter", sa.Integer()),
        sa.Column("resolved_at_chapter", sa.Integer()),
        sa.Column("related_event_id", sa.Text()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("history", sa.Text(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_hooks_work_status", "hooks", ["work_id", "status"])
    op.create_table(
        "timeline",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column("story_time_label", sa.Text(), nullable=False),
        sa.Column("story_time_order", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_flashback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_timeline_work_order", "timeline", ["work_id", "story_time_order"])
    op.create_table(
        "story_events",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("storyline", sa.Text(), nullable=False, server_default="main"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("planned_chapter", sa.Integer()),
        sa.Column("status", sa.Text(), nullable=False, server_default="planned"),
        sa.Column("done_in_chapter", sa.Integer()),
        sa.Column("moved_from_chapter", sa.Integer()),
        sa.Column("depends_on", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.Text(), nullable=False, server_default="user"),
    )
    op.create_index("ix_story_events_work_chapter", "story_events", ["work_id", "planned_chapter"])
    op.create_table(
        "summaries",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("chapter_no", sa.Integer()),
        sa.Column("arc_key", sa.Text()),
        sa.Column("from_chapter", sa.Integer()),
        sa.Column("to_chapter", sa.Integer()),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("key_points", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_hash", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text()),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pinned_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("job_id", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint("level IN ('chapter','arc','synopsis')", name="level_valid"),
    )
    op.create_index(
        "ix_summaries_work_level_current", "summaries", ["work_id", "level", "is_current"]
    )
    op.create_table(
        "context_traces",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Text()),
        sa.Column("job_step_id", sa.Text()),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_id", sa.Text()),
        sa.Column("effort", sa.Text()),
        sa.Column("prompt_versions", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("budget_tokens", sa.Integer()),
        sa.Column("estimated_input_tokens", sa.Integer()),
        sa.Column("counted_input_tokens", sa.Integer()),
        sa.Column("actual_input_tokens", sa.Integer()),
        sa.Column("cache_read_tokens", sa.Integer()),
        sa.Column("cache_write_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("count_method", sa.Text()),
        sa.Column("items", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("compacted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_context_traces_work_chapter_created",
        "context_traces",
        ["work_id", "chapter_no", "created_at"],
    )
    op.create_index("ix_context_traces_job", "context_traces", ["job_id"])
    op.create_table(
        "state_pending_deltas",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("base_chapter_no", sa.Integer(), nullable=False),
        sa.Column("ops", sa.Text(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("result", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint("status IN ('pending','applied','rejected')", name="status_valid"),
    )
    op.create_index("ix_state_pending_work_status", "state_pending_deltas", ["work_id", "status"])
    op.create_table(
        "author_controls",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("control_key", sa.Text(), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("work_id", "control_key"),
    )


def downgrade() -> None:
    for table in (
        "author_controls",
        "state_pending_deltas",
        "context_traces",
        "summaries",
        "story_events",
        "timeline",
        "hooks",
        "facts",
    ):
        op.drop_table(table)
    op.drop_index("ix_story_states_work_chapter", table_name="story_states")
    op.drop_index("uq_story_states_current", table_name="story_states")
    op.drop_table("story_states")
    op.drop_column("chapters", "state_id")
