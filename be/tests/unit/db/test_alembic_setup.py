from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_upgrade_head_works_on_empty_data_root(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[3]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    config.attributes["data_root"] = tmp_path

    command.upgrade(config, "head")

    database = tmp_path / "db" / "app.sqlite3"
    assert database.is_file()
    with create_engine(f"sqlite:///{database.as_posix()}").connect() as connection:
        inspector = inspect(connection)
        assert "alembic_version" in inspector.get_table_names()
        assert {"settings", "jobs", "job_steps", "job_events", "idempotency_records"}.issubset(
            inspector.get_table_names()
        )
        assert "pinned_json" in {column["name"] for column in inspector.get_columns("jobs")}
        event_indexes = inspector.get_indexes("job_events")
        assert any(index["name"] == "ix_job_events_job_id_seq" for index in event_indexes)

    command.downgrade(config, "base")
    with create_engine(f"sqlite:///{database.as_posix()}").connect() as connection:
        assert not (set(inspect(connection).get_table_names()) - {"alembic_version"})
