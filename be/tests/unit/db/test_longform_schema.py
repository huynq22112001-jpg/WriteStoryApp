import asyncio
import sqlite3

from writestory_be.infrastructure.db.migrations import prepare_database


def test_f09_migration_creates_state_and_ledger_tables(tmp_path):
    root = tmp_path / "data"
    (root / "db").mkdir(parents=True)
    asyncio.run(asyncio.to_thread(prepare_database, root))
    with sqlite3.connect(root / "db" / "app.sqlite3") as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {
            "story_states",
            "facts",
            "hooks",
            "timeline",
            "story_events",
            "summaries",
            "context_traces",
            "state_pending_deltas",
            "author_controls",
            "chapter_handoffs",
            "chapter_plans",
            "chapter_candidates",
            "chapter_measurements",
            "findings",
            "outline_proposals",
        } <= tables
        columns = {row[1] for row in connection.execute("PRAGMA table_info(chapters)")}
        assert "state_id" in columns
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(story_states)")}
        assert "uq_story_states_current" in indexes
