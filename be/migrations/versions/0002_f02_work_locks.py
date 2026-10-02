"""Record the work-lock contract introduced in the baseline.

Revision ID: 0002
Revises: 0001

`work_locks` and its lease columns are present in 0001_baseline per F02's canonical schema.
This revision is intentionally a no-op so the prompt sequence retains its declared migration slot.
"""
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
