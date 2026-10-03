"""Add chapter handoffs, plans, candidates, findings, and measurements."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("works", sa.Column("continuity_updated_at", sa.Text()))
    op.add_column(
        "chapters", sa.Column("structure_version", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column("story_states", sa.Column("source_revision_id", sa.Text()))
    op.add_column("story_states", sa.Column("superseded_at", sa.Text()))
    op.create_table(
        "chapter_handoffs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column(
            "revision_id", sa.Text(), sa.ForeignKey("chapter_revisions.id", ondelete="SET NULL")
        ),
        sa.Column("handoff_revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ending_state", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("tail_text", sa.Text()),
        sa.Column("tail_paragraph_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("tail_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tail_counted_for_model", sa.Text()),
        sa.Column("open_threads", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("next_opening_requirements", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("superseded_at", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "uq_handoffs_current",
        "chapter_handoffs",
        ["work_id", "chapter_no"],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
    )
    op.create_table(
        "chapter_plans",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("inputs", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("plan_json", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("edited_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("job_id", sa.Text()),
        sa.Column("model_id", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_chapter_plans_input", "chapter_plans", ["work_id", "chapter_no", "input_hash"]
    )
    op.create_table(
        "chapter_candidates",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "chapter_id",
            sa.Text(),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Text()),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text()),
        sa.Column(
            "parent_candidate_id",
            sa.Text(),
            sa.ForeignKey("chapter_candidates.id", ondelete="SET NULL"),
        ),
        sa.Column("round", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("base_revision_id", sa.Text()),
        sa.Column("scope", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("author_instruction", sa.Text()),
        sa.Column("content_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("plain_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("paragraphs_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("ops_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.Text(), nullable=False, server_default="streaming"),
        sa.Column("stop_reason", sa.Text()),
        sa.Column("continuations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("length_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("check_summary", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("proposed_delta", sa.Text()),
        sa.Column("ending_state", sa.Text()),
        sa.Column("summary_json", sa.Text()),
        sa.Column("seam_json", sa.Text()),
        sa.Column("base_state_id", sa.Text()),
        sa.Column("plan_id", sa.Text(), sa.ForeignKey("chapter_plans.id", ondelete="SET NULL")),
        sa.Column("accepted_paragraph_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("accepted_revision_id", sa.Text()),
        sa.Column("superseded_by", sa.Text()),
        sa.Column("expires_at", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("ready_at", sa.Text()),
        sa.Column("decided_at", sa.Text()),
        sa.CheckConstraint("kind IN ('draft','repair','revise','author')", name="kind_valid"),
        sa.CheckConstraint(
            "status IN ('streaming','partial','ready','accepted','rejected','superseded')",
            name="status_valid",
        ),
    )
    op.create_index("ix_candidates_chapter_status", "chapter_candidates", ["chapter_id", "status"])
    op.create_index("ix_candidates_job", "chapter_candidates", ["job_id"])
    op.create_index("ix_candidates_expiry", "chapter_candidates", ["status", "expires_at"])
    op.create_table(
        "chapter_measurements",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "chapter_id",
            sa.Text(),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.Text()),
        sa.Column(
            "candidate_id", sa.Text(), sa.ForeignKey("chapter_candidates.id", ondelete="SET NULL")
        ),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_measurements_work_chapter", "chapter_measurements", ["work_id", "chapter_no"]
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("chapter_id", sa.Text(), sa.ForeignKey("chapters.id", ondelete="CASCADE")),
        sa.Column("chapter_no", sa.Integer()),
        sa.Column("revision_id", sa.Text()),
        sa.Column(
            "candidate_id", sa.Text(), sa.ForeignKey("chapter_candidates.id", ondelete="CASCADE")
        ),
        sa.Column("job_id", sa.Text()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("check_id", sa.Text()),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Text()),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("message_key", sa.Text()),
        sa.Column("params", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_status", sa.Text(), nullable=False, server_default="verified"),
        sa.Column("suggestion", sa.Text()),
        sa.Column("refs", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("fingerprint", sa.Text()),
        sa.Column("round", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("needs_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("resolution_note", sa.Text()),
        sa.Column("resolved_by", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.Text()),
        sa.CheckConstraint("severity IN ('blocker','major','minor')", name="severity_valid"),
        sa.CheckConstraint("status IN ('open','resolved','dismissed')", name="status_valid"),
        sa.CheckConstraint(
            "evidence_status IN ('verified','unavailable')", name="evidence_status_valid"
        ),
    )
    op.create_index(
        "ix_findings_work_status_severity", "findings", ["work_id", "status", "severity"]
    )
    op.create_index("ix_findings_chapter_status", "findings", ["chapter_id", "status"])
    op.create_index(
        "uq_findings_candidate_fingerprint",
        "findings",
        ["candidate_id", "fingerprint"],
        unique=True,
        sqlite_where=sa.text("candidate_id IS NOT NULL AND fingerprint IS NOT NULL"),
    )
    op.create_table(
        "outline_proposals",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("job_id", sa.Text()),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column("changes_json", sa.Text(), nullable=False),
        sa.Column("pacing_assessment", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("outline_proposals")
    op.drop_index("uq_findings_candidate_fingerprint", table_name="findings")
    op.drop_index("ix_findings_chapter_status", table_name="findings")
    op.drop_index("ix_findings_work_status_severity", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_measurements_work_chapter", table_name="chapter_measurements")
    op.drop_table("chapter_measurements")
    op.drop_index("ix_candidates_expiry", table_name="chapter_candidates")
    op.drop_index("ix_candidates_job", table_name="chapter_candidates")
    op.drop_index("ix_candidates_chapter_status", table_name="chapter_candidates")
    op.drop_table("chapter_candidates")
    op.drop_index("ix_chapter_plans_input", table_name="chapter_plans")
    op.drop_table("chapter_plans")
    op.drop_index("uq_handoffs_current", table_name="chapter_handoffs")
    op.drop_table("chapter_handoffs")
    op.drop_column("story_states", "superseded_at")
    op.drop_column("story_states", "source_revision_id")
    op.drop_column("chapters", "structure_version")
    op.drop_column("works", "continuity_updated_at")
