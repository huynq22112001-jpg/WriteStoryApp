"""Add the shared FTS5 search projection.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("work_id", sa.Text()),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("paragraph_id", sa.Text()),
        sa.Column("chapter_no", sa.Integer()),
        sa.Column("source_revision_id", sa.Text()),
        sa.Column("language", sa.Text(), nullable=False, server_default="vi"),
        sa.Column("title", sa.Text()),
        sa.Column("title_norm", sa.Text()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_norm", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "uq_search_documents_source_paragraph",
        "search_documents",
        ["source_type", "source_id", sa.text("ifnull(paragraph_id, '')")],
        unique=True,
    )
    op.create_index(
        "ix_search_documents_work_id_source_type",
        "search_documents",
        ["work_id", "source_type"],
    )
    op.execute(
        "CREATE VIRTUAL TABLE search_fts USING fts5("
        "title_norm, body_norm, content='search_documents', content_rowid='id', "
        "tokenize='unicode61 remove_diacritics 2')"
    )
    op.execute(
        "CREATE TRIGGER search_documents_ai AFTER INSERT ON search_documents BEGIN "
        "INSERT INTO search_fts(rowid, title_norm, body_norm) "
        "VALUES (new.id, new.title_norm, new.body_norm); END"
    )
    op.execute(
        "CREATE TRIGGER search_documents_ad AFTER DELETE ON search_documents BEGIN "
        "INSERT INTO search_fts(search_fts, rowid, title_norm, body_norm) "
        "VALUES ('delete', old.id, old.title_norm, old.body_norm); END"
    )
    op.execute(
        "CREATE TRIGGER search_documents_au AFTER UPDATE ON search_documents BEGIN "
        "INSERT INTO search_fts(search_fts, rowid, title_norm, body_norm) "
        "VALUES ('delete', old.id, old.title_norm, old.body_norm); "
        "INSERT INTO search_fts(rowid, title_norm, body_norm) "
        "VALUES (new.id, new.title_norm, new.body_norm); END"
    )
    op.execute(
        "CREATE VIRTUAL TABLE search_trigram USING fts5("
        "title_norm, content='', tokenize='trigram')"
    )
    op.execute(
        "CREATE TRIGGER search_documents_trigram_ai AFTER INSERT ON search_documents "
        "WHEN new.source_type IN ('character','location') BEGIN "
        "INSERT INTO search_trigram(rowid, title_norm) VALUES (new.id, new.title_norm); END"
    )
    op.execute(
        "CREATE TRIGGER search_documents_trigram_ad AFTER DELETE ON search_documents "
        "WHEN old.source_type IN ('character','location') BEGIN "
        "INSERT INTO search_trigram(search_trigram, rowid, title_norm) "
        "VALUES ('delete', old.id, old.title_norm); END"
    )
    op.execute(
        "CREATE TRIGGER search_documents_trigram_au AFTER UPDATE ON search_documents BEGIN "
        "INSERT INTO search_trigram(search_trigram, rowid, title_norm) "
        "SELECT 'delete', old.id, old.title_norm "
        "WHERE old.source_type IN ('character','location'); "
        "INSERT INTO search_trigram(rowid, title_norm) "
        "SELECT new.id, new.title_norm WHERE new.source_type IN ('character','location'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS search_documents_trigram_au")
    op.execute("DROP TRIGGER IF EXISTS search_documents_trigram_ad")
    op.execute("DROP TRIGGER IF EXISTS search_documents_trigram_ai")
    op.execute("DROP TRIGGER IF EXISTS search_documents_au")
    op.execute("DROP TRIGGER IF EXISTS search_documents_ad")
    op.execute("DROP TRIGGER IF EXISTS search_documents_ai")
    op.execute("DROP TABLE IF EXISTS search_trigram")
    op.execute("DROP TABLE IF EXISTS search_fts")
    op.drop_table("search_documents")
