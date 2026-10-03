from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from writestory_be.infrastructure.db.base import Base


class StoryStateRow(Base):
    __tablename__ = "story_states"
    __table_args__ = (
        Index(
            "uq_story_states_current",
            "work_id",
            "chapter_no",
            unique=True,
            sqlite_where=text("is_current = 1"),
        ),
        Index("ix_story_states_work_chapter", "work_id", "chapter_no"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("chapter_revisions.id", ondelete="SET NULL")
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    state_hash: Mapped[str] = mapped_column(Text, nullable=False)
    delta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    parent_state_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("story_states.id", ondelete="SET NULL")
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    job_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class Fact(Base):
    __tablename__ = "facts"
    __table_args__ = (Index("ix_facts_work_status", "work_id", "status"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    subject_ref: Mapped[str | None] = mapped_column(Text)
    predicate: Mapped[str] = mapped_column(Text, nullable=False)
    object: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_until_chapter: Mapped[int | None] = mapped_column(Integer)
    source_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    source: Mapped[str] = mapped_column(Text, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    created_state_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("story_states.id", ondelete="SET NULL")
    )
    closed_state_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("story_states.id", ondelete="SET NULL")
    )


class Hook(Base):
    __tablename__ = "hooks"
    __table_args__ = (Index("ix_hooks_work_status", "work_id", "status"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    opened_at_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    due_by_chapter: Mapped[int | None] = mapped_column(Integer)
    payoff_plan: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    last_advanced_chapter: Mapped[int | None] = mapped_column(Integer)
    resolved_at_chapter: Mapped[int | None] = mapped_column(Integer)
    related_event_id: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    history: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class TimelineEntry(Base):
    __tablename__ = "timeline"
    __table_args__ = (Index("ix_timeline_work_order", "work_id", "story_time_order"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    story_time_label: Mapped[str] = mapped_column(Text, nullable=False)
    story_time_order: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_flashback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class StoryEvent(Base):
    __tablename__ = "story_events"
    __table_args__ = (Index("ix_story_events_work_chapter", "work_id", "planned_chapter"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    storyline: Mapped[str] = mapped_column(Text, nullable=False, default="main")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    planned_chapter: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="planned")
    done_in_chapter: Mapped[int | None] = mapped_column(Integer)
    moved_from_chapter: Mapped[int | None] = mapped_column(Integer)
    depends_on: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="user")


class Summary(Base):
    __tablename__ = "summaries"
    __table_args__ = (Index("ix_summaries_work_level_current", "work_id", "level", "is_current"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(Text, nullable=False)
    chapter_no: Mapped[int | None] = mapped_column(Integer)
    arc_key: Mapped[str | None] = mapped_column(Text)
    from_chapter: Mapped[int | None] = mapped_column(Integer)
    to_chapter: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_hash: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pinned_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    job_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ContextTrace(Base):
    __tablename__ = "context_traces"
    __table_args__ = (
        Index("ix_context_traces_work_chapter_created", "work_id", "chapter_no", "created_at"),
        Index("ix_context_traces_job", "job_id"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    job_id: Mapped[str | None] = mapped_column(Text)
    job_step_id: Mapped[str | None] = mapped_column(Text)
    step: Mapped[str] = mapped_column(Text, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_id: Mapped[str | None] = mapped_column(Text)
    effort: Mapped[str | None] = mapped_column(Text)
    prompt_versions: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    budget_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_input_tokens: Mapped[int | None] = mapped_column(Integer)
    counted_input_tokens: Mapped[int | None] = mapped_column(Integer)
    actual_input_tokens: Mapped[int | None] = mapped_column(Integer)
    cache_read_tokens: Mapped[int | None] = mapped_column(Integer)
    cache_write_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    count_method: Mapped[str | None] = mapped_column(Text)
    items: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compacted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class StatePendingDelta(Base):
    __tablename__ = "state_pending_deltas"
    __table_args__ = (Index("ix_state_pending_work_status", "work_id", "status"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    base_chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    ops: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    result: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class AuthorControl(Base):
    __tablename__ = "author_controls"
    __table_args__ = (UniqueConstraint("work_id", "control_key"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    control_key: Mapped[str] = mapped_column(Text, nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
