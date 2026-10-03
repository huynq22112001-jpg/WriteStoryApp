from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from writestory_be.infrastructure.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class Work(Base):
    __tablename__ = "works"
    __table_args__ = (
        CheckConstraint("language = 'vi'", name="language_vi"),
        CheckConstraint("status IN ('draft','ready','archived')", name="status_valid"),
        CheckConstraint(
            "continuity_status IN ('ok','blocked_needs_resync','stale_from')",
            name="continuity_status_valid",
        ),
        CheckConstraint(
            "autowrite_mode_default IN ('auto','review_each','review_every_k')",
            name="autowrite_mode_valid",
        ),
        CheckConstraint("chapter_length_min < chapter_length_max", name="chapter_length_valid"),
        CheckConstraint(
            "(continuity_status = 'stale_from' AND continuity_chapter_no IS NOT NULL "
            "AND continuity_reason IS NOT NULL) OR (continuity_status != 'stale_from' "
            "AND continuity_chapter_no IS NULL AND continuity_reason IS NULL)",
            name="continuity_stale_fields",
        ),
        CheckConstraint(
            "autowrite_mode_default != 'review_every_k' OR review_every_k IS NOT NULL",
            name="review_every_k_required",
        ),
        Index("ix_works_deleted_updated", "deleted_at", "updated_at"),
        Index("ix_works_status", "status"),
        Index("ix_works_genre", "genre"),
        Index("ix_works_last_opened", "last_opened_at"),
        Index("ix_works_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        Text, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_search: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False, default="vi", server_default="vi")
    genre: Mapped[str | None] = mapped_column(Text)
    genre_label_custom: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="draft", server_default="draft"
    )
    brief: Mapped[str | None] = mapped_column(Text)
    target_chapters: Mapped[int | None] = mapped_column(Integer)
    chapter_length_min: Mapped[int] = mapped_column(Integer, nullable=False, default=2500)
    chapter_length_max: Mapped[int] = mapped_column(Integer, nullable=False, default=3500)
    autowrite_mode_default: Mapped[str] = mapped_column(
        Text, nullable=False, default="auto", server_default="auto"
    )
    review_every_k: Mapped[int | None] = mapped_column(Integer)
    max_repair_rounds: Mapped[int | None] = mapped_column(Integer)
    budget_daily_usd: Mapped[float | None] = mapped_column(Float)
    budget_daily_tokens: Mapped[int | None] = mapped_column(Integer)
    continuity_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="ok", server_default="ok"
    )
    continuity_chapter_no: Mapped[int | None] = mapped_column(Integer)
    continuity_reason: Mapped[str | None] = mapped_column(Text)
    cover_asset_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("assets.id", ondelete="SET NULL")
    )
    wizard_step: Mapped[str | None] = mapped_column(Text)
    wizard_completed_steps: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]", server_default="[]"
    )
    last_opened_at: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[str | None] = mapped_column(Text)


class StyleProfile(Base):
    __tablename__ = "style_profile"
    __table_args__ = (
        CheckConstraint(
            "vocab_register IN ('han_viet','balanced','thuan_viet')", name="vocab_valid"
        ),
        CheckConstraint("dialogue_style IN ('dash','quotes')", name="dialogue_valid"),
        CheckConstraint("tone_mark_style IN ('old','new')", name="tone_mark_valid"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    vocab_register: Mapped[str] = mapped_column(Text, nullable=False, default="balanced")
    dialogue_style: Mapped[str] = mapped_column(Text, nullable=False, default="dash")
    dialogue_dash_char: Mapped[str | None] = mapped_column(Text)
    tone_mark_style: Mapped[str] = mapped_column(Text, nullable=False, default="new")
    punctuation_rules: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    banned_phrases: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    voice: Mapped[str | None] = mapped_column(Text)
    voice_samples: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
