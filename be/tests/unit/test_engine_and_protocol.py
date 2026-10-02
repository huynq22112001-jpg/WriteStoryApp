import pytest
from sqlalchemy import text

from writestory_be.bootstrap.context import DATA_SUBDIRS, prepare_data_root
from writestory_be.bootstrap.protocol import (
    BootstrapConfig,
    ProtocolMismatchError,
    parse_bootstrap_line,
)
from writestory_be.core.clock import to_iso, utcnow
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.engine import create_engine, database_path


async def test_sqlite_pragmas_applied(tmp_path):
    engine = create_engine(database_path(tmp_path))
    try:
        async with engine.connect() as conn:
            journal = (await conn.execute(text("PRAGMA journal_mode"))).scalar_one()
            fk = (await conn.execute(text("PRAGMA foreign_keys"))).scalar_one()
            sync = (await conn.execute(text("PRAGMA synchronous"))).scalar_one()
            busy = (await conn.execute(text("PRAGMA busy_timeout"))).scalar_one()
    finally:
        await engine.dispose()
    assert journal.lower() == "wal"
    assert fk == 1
    assert sync == 2  # FULL
    assert busy == 5000


def test_prepare_data_root_creates_layout(tmp_path):
    root = tmp_path / "Truyện của tôi" / "data"  # đường dẫn Unicode + khoảng trắng
    prepare_data_root(root)
    assert all((root / name).is_dir() for name in DATA_SUBDIRS)
    assert list((root / "tmp").iterdir()) == []


def test_bootstrap_line_roundtrip_and_token_hidden(tmp_path):
    line = BootstrapConfig(
        protocol_version=1, token="bi-mat", data_root=tmp_path
    ).model_dump_json()
    config = parse_bootstrap_line(line)
    assert config.token == "bi-mat"
    assert "bi-mat" not in repr(config)


def test_bootstrap_protocol_mismatch(tmp_path):
    line = BootstrapConfig(protocol_version=99, token="x", data_root=tmp_path).model_dump_json()
    with pytest.raises(ProtocolMismatchError):
        parse_bootstrap_line(line)


def test_ids_are_uuid7_and_sortable():
    ids = [new_id() for _ in range(50)]
    assert all(i[14] == "7" for i in ids)
    assert ids == sorted(ids)


def test_iso_format():
    s = to_iso(utcnow())
    assert s.endswith("Z") and len(s) == len("2026-10-02T03:04:05.123Z")
