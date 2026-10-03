from fastapi import APIRouter

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.modules.language.schemas import (
    NormalizeIn,
    NormalizeOut,
    SlopListOut,
    SlopListPut,
    TextCheckIn,
    TextCheckOut,
)
from writestory_be.modules.language.service import LanguageService

router = APIRouter(tags=["languages"])


@router.get("/v1/languages/{code}/genre-presets", name="language_genre_presets")
async def genre_presets(code: str, runtime: RuntimeDep):
    return await LanguageService(runtime).genre_presets(code)


@router.get("/v1/languages/{code}/slop-list", response_model=SlopListOut, name="get_slop_list")
async def get_slop_list(code: str, runtime: RuntimeDep):
    return await LanguageService(runtime).slop_list(code)


@router.put("/v1/languages/{code}/slop-list", name="put_slop_list")
async def put_slop_list(code: str, body: SlopListPut, runtime: RuntimeDep):
    return await LanguageService(runtime).put_slop_list(code, body)


@router.post(
    "/v1/languages/{code}/normalize", response_model=NormalizeOut, name="normalize_language_text"
)
async def normalize_text(code: str, body: NormalizeIn, runtime: RuntimeDep):
    return await LanguageService(runtime).normalize_text(code, body)


@router.post("/v1/works/{work_id}/text/check", response_model=TextCheckOut, name="check_work_text")
async def check_work_text(work_id: str, body: TextCheckIn, runtime: RuntimeDep):
    return await LanguageService(runtime).check_text(work_id, body)
