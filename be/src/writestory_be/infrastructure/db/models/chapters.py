from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from writestory_be.infrastructure.db.base import Base


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','drafting','checking','revising','waiting_user','committed')",
            name="status_valid",
        ),
        Index(
            "uq_chapters_work_no_active",
            "work_id",
            "chapter_no",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index("ix_chapters_work_no", "work_id", "chapter_no"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="draft", server_default="draft"
    )
    state_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    current_revision_id: Mapped[str | None] = mapped_column(Text)
    revision_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    syllable_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[str | None] = mapped_column(Text)


class ChapterRevision(Base):
    __tablename__ = "chapter_revisions"
    __table_args__ = (
        UniqueConstraint("chapter_id", "revision_no"),
        Index("ix_chapter_revisions_created", "chapter_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    chapter_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_revision_id: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    doc_json: Mapped[str] = mapped_column(Text, nullable=False)
    plain_text: Mapped[str] = mapped_column(Text, nullable=False)
    paragraphs_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    syllable_count: Mapped[int] = mapped_column(Integer, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    restored_from_revision_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ChapterWorkingCopy(Base):
    __tablename__ = "chapter_working_copy"
    chapter_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True
    )
    base_revision_id: Mapped[str | None] = mapped_column(Text)
    doc_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    has_changes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    client_session_id: Mapped[str | None] = mapped_column(Text)
    client_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
