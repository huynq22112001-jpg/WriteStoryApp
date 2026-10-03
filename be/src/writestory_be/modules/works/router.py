from typing import Literal

from fastapi import APIRouter, Query, Request, Response, status

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.api.idempotency import idempotency_key_from_request
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.modules.works.schemas import (
    StyleProfileIn,
    StyleProfileOut,
    WorkCreate,
    WorkListResponse,
    WorkOut,
    WorkPatch,
    WorkStatus,
)
from writestory_be.modules.works.service import WorkService, genres

router = APIRouter(tags=["works"])
STATUS_QUERY = Query(default=None, alias="status")


@router.get("/v1/works", response_model=WorkListResponse, name="list_works")
async def list_works(
    runtime: RuntimeDep,
    q: str | None = None,
    genre: str | None = None,
    status_filter: WorkStatus | None = STATUS_QUERY,
    continuity: Literal["ok", "blocked_needs_resync", "stale_from"] | None = None,
    sort: Literal["updated", "opened", "title"] = "updated",
    cursor: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    return await WorkService(runtime).list_works(
        q=q,
        genre=genre,
        status=status_filter,
        continuity=continuity,
        sort=sort,
        cursor=cursor,
        limit=limit,
    )


@router.post(
    "/v1/works", response_model=WorkOut, status_code=status.HTTP_201_CREATED, name="create_work"
)
async def create_work(body: WorkCreate, request: Request, runtime: RuntimeDep):
    key = idempotency_key_from_request(request)
    _, result = await WorkService(runtime).create(body, key)
    return result


@router.get("/v1/works/{work_id}", response_model=WorkOut, name="get_work")
async def get_work(work_id: str, runtime: RuntimeDep):
    return await WorkService(runtime).get(work_id)


@router.patch("/v1/works/{work_id}", response_model=WorkOut, name="patch_work")
async def patch_work(work_id: str, body: WorkPatch, runtime: RuntimeDep):
    return await WorkService(runtime).patch(work_id, body)


@router.delete("/v1/works/{work_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_work")
async def delete_work(work_id: str, runtime: RuntimeDep):
    await WorkService(runtime).delete(work_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/v1/works/{work_id}/open", status_code=status.HTTP_204_NO_CONTENT, name="open_work")
async def open_work(work_id: str, request: Request, runtime: RuntimeDep):
    key = idempotency_key_from_request(request)
    await WorkService(runtime).open(work_id, key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/v1/works/{work_id}/style-profile",
    response_model=StyleProfileOut,
    name="get_style_profile",
)
async def get_style_profile(work_id: str, runtime: RuntimeDep):
    return await WorkService(runtime).get_style_profile(work_id)


@router.put(
    "/v1/works/{work_id}/style-profile",
    response_model=StyleProfileOut,
    name="put_style_profile",
)
async def put_style_profile(work_id: str, body: StyleProfileIn, runtime: RuntimeDep):
    return await WorkService(runtime).put_style_profile(work_id, body)


@router.get("/v1/languages", name="list_languages")
async def list_languages():
    return [{"code": "vi", "label": "Tiếng Việt", "enabled": True}]


@router.get("/v1/languages/{code}/genres", name="list_genres")
async def list_genres(code: str):
    if code != "vi":
        raise AppError(ErrorCode.NOT_FOUND)
    return await genres()
