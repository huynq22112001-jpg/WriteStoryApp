import json
import sqlite3

import pytest

from writestory_be.infrastructure.db.migrations import DatabaseStartupError, prepare_database


def test_prepare_database_initializes_once_and_reports_schema(tmp_path) -> None:
    stages = []
    revision = prepare_database(tmp_path, stages.append, data_id="test-data")
    database = tmp_path / "db" / "app.sqlite3"
    marker = json.loads((tmp_path / ".writestory-data.json").read_text(encoding="utf-8"))

    assert revision == "0003"
    assert stages == ["migrating", "reconciling"]
    assert marker["db_initialized"] is True
    assert marker["data_id"] == "test-data"
    assert prepare_database(tmp_path, stages.append, data_id="test-data") == revision
    assert stages == ["migrating", "reconciling", "reconciling"]
    assert database.is_file()


def test_initialized_marker_without_database_is_fatal(tmp_path) -> None:
    (tmp_path / ".writestory-data.json").write_text(
        json.dumps({"db_initialized": True}), encoding="utf-8"
    )
    with pytest.raises(DatabaseStartupError) as error:
        prepare_database(tmp_path)
    assert error.value.code == "DB_MISSING"


def test_unknown_schema_revision_is_rejected(tmp_path) -> None:
    database = tmp_path / "db" / "app.sqlite3"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES ('future_revision')")

    with pytest.raises(DatabaseStartupError) as error:
        prepare_database(tmp_path)
    assert error.value.code == "SCHEMA_TOO_NEW"
