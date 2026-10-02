"""Baseline tables for durable jobs and system data.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("idempotency_key", sa.Text(), unique=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("work_id", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("wait_reason", sa.Text()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queue_position", sa.Integer()),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("base_revision_id", sa.Text()),
        sa.Column("stage", sa.Text()),
        sa.Column("progress_json", sa.Text()),
        sa.Column("checkpoint_json", sa.Text()),
        sa.Column("pinned_json", sa.Text()),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancel_requested_at", sa.Text()),
        sa.Column("error_code", sa.Text()),
        sa.Column("error_json", sa.Text()),
        sa.Column("usage_json", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text()),
        sa.Column("finished_at", sa.Text()),
        sa.Column("interrupted_at", sa.Text()),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('queued','waiting_slot','running','waiting_user','blocked',"
            "'succeeded','failed','cancelled','interrupted')",
            name="ck_jobs_status_valid",
        ),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_work_id_status", "jobs", ["work_id", "status"])
    op.create_index("ix_jobs_work_id_queue_position", "jobs", ["work_id", "queue_position"])
    op.create_table(
        "job_steps",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "job_id", sa.Text(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text()),
        sa.Column("output_hash", sa.Text()),
        sa.Column("checkpoint_json", sa.Text()),
        sa.Column("prompt_id", sa.Text()),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("model_id", sa.Text()),
        sa.Column("effort", sa.Text()),
        sa.Column("usage_json", sa.Text()),
        sa.Column("error_code", sa.Text()),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("finished_at", sa.Text()),
        sa.UniqueConstraint("job_id", "step", "attempt", "round", name="uq_job_steps_job_id"),
    )
    op.create_index("ix_job_steps_job_id_started_at", "job_steps", ["job_id", "started_at"])
    op.create_table(
        "job_events",
        sa.Column("seq", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("v", sa.Integer(), nullable=False),
        sa.Column("ts", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("work_id", sa.Text()),
        sa.Column("job_id", sa.Text()),
        sa.Column("chapter_no", sa.Integer()),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_job_events_ts", "job_events", ["ts"])
    op.create_index("ix_job_events_work_id_seq", "job_events", ["work_id", "seq"])
    op.create_index("ix_job_events_job_id_seq", "job_events", ["job_id", "seq"])
    op.create_table(
        "idempotency_records",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("method", sa.Text(), primary_key=True),
        sa.Column("path", sa.Text(), primary_key=True),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_idempotency_expires", "idempotency_records", ["expires_at"])
    op.create_table(
        "work_locks",
        sa.Column("work_id", sa.Text(), primary_key=True),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("acquired_at", sa.Text(), nullable=False),
        sa.Column("heartbeat_at", sa.Text(), nullable=False),
        sa.Column("lease_expires_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_work_locks_lease_expires_at", "work_locks", ["lease_expires_at"])
    op.create_table(
        "assets",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("work_id", sa.Text()),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("rel_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("original_name", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="ready"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("rel_path", name="uq_assets_rel_path"),
        sa.CheckConstraint(
            "status IN ('ready','missing','deleted')", name="ck_assets_status_valid"
        ),
    )
    op.create_index("ix_assets_work_id", "assets", ["work_id"])
    op.create_index("ix_assets_sha256", "assets", ["sha256"])


def downgrade() -> None:
    op.drop_table("assets")
    op.drop_table("work_locks")
    op.drop_table("idempotency_records")
    op.drop_table("job_events")
    op.drop_table("job_steps")
    op.drop_table("jobs")
    op.drop_table("settings")
