from fastapi import APIRouter, Response, status

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.modules.chapters.schemas import (
    ChapterCreate,
    ReorderIn,
    ReplaceIn,
    RestoreIn,
    SnapshotIn,
    WorkingCopyIn,
)
from writestory_be.modules.chapters.service import ChapterService

router = APIRouter(tags=["chapters"])


@router.get("/v1/chapters/{chapter_id}", name="get_chapter")
async def get_chapter(chapter_id: str, runtime: RuntimeDep):
    return await ChapterService(runtime).get(chapter_id)


@router.get("/v1/works/{work_id}/chapters", name="list_chapters")
async def list_chapters(work_id: str, runtime: RuntimeDep):
    return await ChapterService(runtime).list(work_id)


@router.post(
    "/v1/works/{work_id}/chapters", status_code=status.HTTP_201_CREATED, name="create_chapter"
)
async def create_chapter(work_id: str, body: ChapterCreate, runtime: RuntimeDep):
    return await ChapterService(runtime).create(work_id, body)


@router.post("/v1/works/{work_id}/chapters/reorder", name="reorder_chapters")
async def reorder_chapters(work_id: str, body: ReorderIn, runtime: RuntimeDep):
    return await ChapterService(runtime).reorder(work_id, body.chapter_ids)


@router.delete(
    "/v1/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_chapter"
)
async def delete_chapter(chapter_id: str, runtime: RuntimeDep):
    await ChapterService(runtime).delete(chapter_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/v1/chapters/{chapter_id}/working-copy", name="get_working_copy")
async def get_working_copy(chapter_id: str, runtime: RuntimeDep):
    return await ChapterService(runtime).get_working_copy(chapter_id)


@router.put("/v1/chapters/{chapter_id}/working-copy", name="save_working_copy")
async def save_working_copy(chapter_id: str, body: WorkingCopyIn, runtime: RuntimeDep):
    return await ChapterService(runtime).save_working_copy(chapter_id, body)


@router.post("/v1/chapters/{chapter_id}/snapshot", name="snapshot_chapter")
async def snapshot_chapter(chapter_id: str, body: SnapshotIn, runtime: RuntimeDep):
    return await ChapterService(runtime).snapshot(chapter_id, body.reason, body.expected_revision)


@router.put("/v1/chapters/{chapter_id}", name="replace_chapter")
async def replace_chapter(chapter_id: str, body: ReplaceIn, runtime: RuntimeDep):
    return await ChapterService(runtime).replace(chapter_id, body)


@router.get("/v1/chapters/{chapter_id}/revisions", name="list_chapter_revisions")
async def list_revisions(chapter_id: str, runtime: RuntimeDep):
    return await ChapterService(runtime).revisions(chapter_id)


@router.get("/v1/chapters/{chapter_id}/revisions/{revision_id}", name="get_chapter_revision")
async def get_revision(chapter_id: str, revision_id: str, runtime: RuntimeDep):
    revisions = await ChapterService(runtime).revisions(chapter_id)
    revision = next((item for item in revisions if item["id"] == revision_id), None)
    if revision is None:
        raise AppError(ErrorCode.NOT_FOUND)
    return revision


@router.get(
    "/v1/chapters/{chapter_id}/revisions/{before_id}/diff/{after_id}", name="diff_chapter_revisions"
)
async def diff_revisions(chapter_id: str, before_id: str, after_id: str, runtime: RuntimeDep):
    return await ChapterService(runtime).diff(chapter_id, before_id, after_id)


@router.post(
    "/v1/chapters/{chapter_id}/revisions/{revision_id}/restore", name="restore_chapter_revision"
)
async def restore_revision(chapter_id: str, revision_id: str, body: RestoreIn, runtime: RuntimeDep):
    return await ChapterService(runtime).restore(chapter_id, revision_id, body.expected_revision)
