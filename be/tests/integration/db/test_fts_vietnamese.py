import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker

from writestory_be.infrastructure.db.engine import create_engine, database_path
from writestory_be.infrastructure.db.fts import rebuild_fts, search, upsert_document
from writestory_be.infrastructure.db.unit_of_work import UnitOfWork
from writestory_be.infrastructure.db.writer import WriterQueue


@pytest.mark.asyncio
async def test_fts_matches_vietnamese_words_and_rebuild_preserves_results(tmp_path: Path) -> None:
    project_root = await asyncio.to_thread(lambda: Path(__file__).resolve().parents[3])
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    config.attributes["data_root"] = tmp_path
    await asyncio.to_thread(command.upgrade, config, "head")

    engine = create_engine(database_path(tmp_path))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer = WriterQueue(sessions)
    uow = UnitOfWork(sessions, writer)
    documents = [
        ("one", "chapter", "Đường qua rừng", "Nguyễn bước đi"),
        ("two", "chapter", "Món ăn", "Một bát Ộc nóng"),
        ("three", "character", "Nguyễn An", "Người gác cổng"),
    ]

    async def add_documents(ctx):
        for source_id, source_type, title, body in documents:
            await upsert_document(
                ctx,
                source_type=source_type,
                source_id=source_id,
                title=title,
                body=body,
                work_id="work-a",
            )

    await uow.write(add_documents)
    async with sessions() as session:
        results = {
            query: await search(session, query, work_id="work-a")
            for query in ("nguyen", "oc", "duong")
        }
    assert "one" in {item["source_id"] for item in results["nguyen"]}
    assert "two" in {item["source_id"] for item in results["oc"]}
    assert "one" in {item["source_id"] for item in results["duong"]}

    async def rebuild(ctx):
        await rebuild_fts(ctx.session)

    await uow.write(rebuild)
    async with sessions() as session:
        rebuilt = await search(session, "nguyen", work_id="work-a")
    assert {item["source_id"] for item in rebuilt} == {
        item["source_id"] for item in results["nguyen"]
    }
    await writer.close()
    await engine.dispose()
