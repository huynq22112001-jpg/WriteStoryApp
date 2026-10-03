from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from writestory_be.infrastructure.db.base import Base


class ChapterHandoff(Base):
    __tablename__ = "chapter_handoffs"
    __table_args__ = (
        Index(
            "uq_handoffs_current",
            "work_id",
            "chapter_no",
            unique=True,
            sqlite_where=text("is_current = 1"),
        ),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("chapter_revisions.id", ondelete="SET NULL")
    )
    handoff_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ending_state: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    tail_text: Mapped[str | None] = mapped_column(Text)
    tail_paragraph_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    tail_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tail_counted_for_model: Mapped[str | None] = mapped_column(Text)
    open_threads: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    next_opening_requirements: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    source: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    superseded_at: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ChapterPlanRow(Base):
    __tablename__ = "chapter_plans"
    __table_args__ = (Index("ix_chapter_plans_input", "work_id", "chapter_no", "input_hash"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    input_hash: Mapped[str] = mapped_column(Text, nullable=False)
    inputs: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    edited_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    job_id: Mapped[str | None] = mapped_column(Text)
    model_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ChapterCandidate(Base):
    __tablename__ = "chapter_candidates"
    __table_args__ = (
        Index("ix_candidates_chapter_status", "chapter_id", "status"),
        Index("ix_candidates_job", "job_id"),
        Index("ix_candidates_expiry", "status", "expires_at"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    job_id: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str | None] = mapped_column(Text)
    parent_candidate_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("chapter_candidates.id", ondelete="SET NULL")
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    base_revision_id: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    author_instruction: Mapped[str | None] = mapped_column(Text)
    content_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    plain_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    paragraphs_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    ops_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="streaming")
    stop_reason: Mapped[str | None] = mapped_column(Text)
    continuations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    length_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    check_summary: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    proposed_delta: Mapped[str | None] = mapped_column(Text)
    ending_state: Mapped[str | None] = mapped_column(Text)
    summary_json: Mapped[str | None] = mapped_column(Text)
    seam_json: Mapped[str | None] = mapped_column(Text)
    base_state_id: Mapped[str | None] = mapped_column(Text)
    plan_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("chapter_plans.id", ondelete="SET NULL")
    )
    accepted_paragraph_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    accepted_revision_id: Mapped[str | None] = mapped_column(Text)
    superseded_by: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    ready_at: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[str | None] = mapped_column(Text)


class ChapterMeasurement(Base):
    __tablename__ = "chapter_measurements"
    __table_args__ = (Index("ix_measurements_work_chapter", "work_id", "chapter_no"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_id: Mapped[str | None] = mapped_column(Text)
    candidate_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("chapter_candidates.id", ondelete="SET NULL")
    )
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_findings_work_status_severity", "work_id", "status", "severity"),
        Index("ix_findings_chapter_status", "chapter_id", "status"),
        Index(
            "uq_findings_candidate_fingerprint",
            "candidate_id",
            "fingerprint",
            unique=True,
            sqlite_where=text("candidate_id IS NOT NULL AND fingerprint IS NOT NULL"),
        ),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("chapters.id", ondelete="CASCADE")
    )
    chapter_no: Mapped[int | None] = mapped_column(Integer)
    revision_id: Mapped[str | None] = mapped_column(Text)
    candidate_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("chapter_candidates.id", ondelete="CASCADE")
    )
    job_id: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    check_id: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    message_key: Mapped[str | None] = mapped_column(Text)
    params: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evidence_status: Mapped[str] = mapped_column(Text, nullable=False, default="verified")
    suggestion: Mapped[str | None] = mapped_column(Text)
    refs: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    fingerprint: Mapped[str | None] = mapped_column(Text)
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    needs_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[str | None] = mapped_column(Text)


class OutlineProposal(Base):
    __tablename__ = "outline_proposals"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[str | None] = mapped_column(Text)
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    changes_json: Mapped[str] = mapped_column(Text, nullable=False)
    pacing_assessment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[str | None] = mapped_column(Text)
