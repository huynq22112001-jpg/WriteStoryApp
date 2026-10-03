from fastapi import APIRouter, Query, Response, status
from sqlalchemy import delete, select

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.db.models.providers import (
    Provider,
    ProviderLimit,
    ProviderModel,
    RoleModel,
)
from writestory_be.infrastructure.db.models.system import Setting
from writestory_be.infrastructure.db.models.works import Work
from writestory_be.modules.providers.schemas import (
    AppLimitsIn,
    LimitsIn,
    ModelsPut,
    ProviderIn,
    ProviderPatch,
    ProviderTestIn,
    RolesPut,
)
from writestory_be.modules.providers.service import ProviderService

router = APIRouter(prefix="/v1", tags=["providers"])

APP_LIMIT_KEYS = {
    "worker_pool": "scheduler.worker_pool",
    "app_daily_usd": "budget.app_daily_usd",
    "app_daily_tokens": "budget.app_daily_tokens",
    "work_daily_usd_default": "budget.work_daily_usd_default",
    "timezone": "budget.timezone",
    "autowrite_mode_default": "writing.autowrite_mode_default",
    "review_every_k": "writing.review_every_k",
    "max_repair_rounds": "writing.max_repair_rounds",
    "chapter_length_min": "writing.chapter_length_min",
    "chapter_length_max": "writing.chapter_length_max",
}


@router.get("/settings/limits", name="get_app_limits")
async def get_app_limits(runtime: RuntimeDep):
    async def read(session):
        rows = (
            await session.scalars(select(Setting).where(Setting.key.in_(APP_LIMIT_KEYS.values())))
        ).all()
        values = {row.key: __import__("json").loads(row.value_json) for row in rows}
        return {
            field: values.get(key, default)
            for field, key, default in (
                ("worker_pool", APP_LIMIT_KEYS["worker_pool"], 4),
                ("app_daily_usd", APP_LIMIT_KEYS["app_daily_usd"], None),
                ("app_daily_tokens", APP_LIMIT_KEYS["app_daily_tokens"], None),
                ("work_daily_usd_default", APP_LIMIT_KEYS["work_daily_usd_default"], None),
                ("timezone", APP_LIMIT_KEYS["timezone"], "Asia/Bangkok"),
                ("autowrite_mode_default", APP_LIMIT_KEYS["autowrite_mode_default"], "review_each"),
                ("review_every_k", APP_LIMIT_KEYS["review_every_k"], 5),
                ("max_repair_rounds", APP_LIMIT_KEYS["max_repair_rounds"], 2),
                ("chapter_length_min", APP_LIMIT_KEYS["chapter_length_min"], 1500),
                ("chapter_length_max", APP_LIMIT_KEYS["chapter_length_max"], 2500),
            )
        }

    return await runtime.ensure_database_services().read(read)


@router.put("/settings/limits", name="put_app_limits")
async def put_app_limits(body: AppLimitsIn, runtime: RuntimeDep):
    values = body.model_dump()

    async def write(ctx):
        for field, value in values.items():
            key = APP_LIMIT_KEYS[field]
            row = await ctx.session.get(Setting, key)
            encoded = __import__("json").dumps(value)
            if row is None:
                ctx.session.add(Setting(key=key, value_json=encoded, updated_at=utcnow_iso()))
            else:
                row.value_json = encoded
                row.updated_at = utcnow_iso()
        return values

    return await runtime.ensure_database_services().write(write)


@router.get("/providers", name="list_providers")
async def list_providers(runtime: RuntimeDep):
    return await ProviderService(runtime).list()


@router.post("/providers", status_code=status.HTTP_201_CREATED, name="create_provider")
async def create_provider(body: ProviderIn, runtime: RuntimeDep):
    return await ProviderService(runtime).create(body)


@router.patch("/providers/{provider_id}", name="patch_provider")
async def patch_provider(provider_id: str, body: ProviderPatch, runtime: RuntimeDep):
    return await ProviderService(runtime).patch(provider_id, body)


@router.delete(
    "/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_provider"
)
async def delete_provider(provider_id: str, runtime: RuntimeDep):
    await ProviderService(runtime).delete(provider_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/providers/{provider_id}/discover", name="discover_provider_models")
async def discover_provider(provider_id: str, runtime: RuntimeDep):
    return await ProviderService(runtime).discover(provider_id)


@router.get("/providers/{provider_id}/models", name="get_provider_models")
async def get_provider_models(provider_id: str, runtime: RuntimeDep):
    return await ProviderService(runtime).models(provider_id)


@router.put("/providers/{provider_id}/models", name="put_provider_models")
async def put_provider_models(provider_id: str, body: ModelsPut, runtime: RuntimeDep):
    return await ProviderService(runtime).put_models(
        provider_id, body.expected_revision, body.items
    )


@router.get("/providers/{provider_id}/limits", name="get_provider_limits")
async def get_provider_limits(provider_id: str, runtime: RuntimeDep):
    async def read(session):
        row = await session.get(ProviderLimit, provider_id)
        if row is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return {
            "provider_id": row.provider_id,
            "max_concurrent_requests": row.max_concurrent_requests,
            "rpm": row.rpm,
            "tpm": row.tpm,
            "max_retries": row.max_retries,
            "cooldown_until": row.cooldown_until,
        }

    return await runtime.ensure_database_services().read(read)


@router.put("/providers/{provider_id}/limits", name="put_provider_limits")
async def put_provider_limits(provider_id: str, body: LimitsIn, runtime: RuntimeDep):
    async def write(ctx):
        provider = await ctx.session.get(Provider, provider_id)
        if provider is None:
            raise AppError(ErrorCode.NOT_FOUND)
        row = await ctx.session.get(ProviderLimit, provider_id)
        if row is None:
            row = ProviderLimit(provider_id=provider_id, updated_at=utcnow_iso())
            ctx.session.add(row)
        row.max_concurrent_requests = body.max_concurrent_requests
        row.rpm = body.rpm
        row.tpm = body.tpm
        row.max_retries = body.max_retries
        row.updated_at = utcnow_iso()
        return {
            "provider_id": provider_id,
            "max_concurrent_requests": row.max_concurrent_requests,
            "rpm": row.rpm,
            "tpm": row.tpm,
            "max_retries": row.max_retries,
            "cooldown_until": row.cooldown_until,
        }

    result = await runtime.ensure_database_services().write(write)
    await runtime.provider_limiter.configure(
        provider_id,
        max_concurrent_requests=body.max_concurrent_requests,
        rpm=body.rpm,
        tpm=body.tpm,
    )
    return result


@router.get("/settings/roles", name="get_role_models")
async def get_role_models(runtime: RuntimeDep, work_id: str | None = Query(default=None)):
    uow = runtime.ensure_database_services()

    async def read(session):
        if work_id and await session.get(Work, work_id) is None:
            raise AppError(ErrorCode.NOT_FOUND)
        roles = (await session.scalars(select(RoleModel).where(RoleModel.work_id == work_id))).all()
        result = []
        for role in ("planner", "writer", "checker", "reviewer", "summary"):
            app = await session.scalar(
                select(RoleModel).where(RoleModel.work_id.is_(None), RoleModel.role == role)
            )
            custom = next((row for row in roles if row.role == role), None)
            selected = custom or app
            result.append(
                {
                    "role": role,
                    "provider_id": selected.provider_id if selected else None,
                    "model_id": selected.model_id if selected else None,
                    "effort": selected.effort if selected else None,
                    "inherited_from": "work" if custom else "app" if app else "default",
                }
            )
        return {"scope": "work" if work_id else "app", "roles": result}

    return await uow.read(read)


@router.put("/settings/roles", name="put_role_models")
async def put_role_models(
    body: RolesPut, runtime: RuntimeDep, work_id: str | None = Query(default=None)
):
    if len({row.role for row in body.roles}) != len(body.roles):
        raise AppError(ErrorCode.VALIDATION, detail={"reason": "duplicate_role"})
    uow = runtime.ensure_database_services()

    async def write(ctx):
        session = ctx.session
        if work_id and await session.get(Work, work_id) is None:
            raise AppError(ErrorCode.NOT_FOUND)
        await session.execute(delete(RoleModel).where(RoleModel.work_id == work_id))
        for assignment in body.roles:
            if assignment.provider_id and assignment.model_id:
                model = await session.scalar(
                    select(ProviderModel).where(
                        ProviderModel.provider_id == assignment.provider_id,
                        ProviderModel.model_id == assignment.model_id,
                    )
                )
                if model is None:
                    raise AppError(
                        ErrorCode.VALIDATION,
                        detail={"reason": "model_not_available", "role": assignment.role},
                    )
                allowed = (
                    __import__("json").loads(model.allowed_roles_json)
                    if model.allowed_roles_json
                    else None
                )
                if allowed and assignment.role not in allowed:
                    raise AppError(
                        ErrorCode.VALIDATION,
                        detail={"reason": "role_not_allowed", "role": assignment.role},
                    )
                efforts = (
                    __import__("json").loads(model.supported_efforts_json)
                    if model.supported_efforts_json
                    else None
                )
                if assignment.effort and efforts is not None and assignment.effort not in efforts:
                    raise AppError(
                        ErrorCode.VALIDATION,
                        detail={"reason": "effort_unsupported", "role": assignment.role},
                    )
            session.add(
                RoleModel(
                    id=__import__("writestory_be.core.ids", fromlist=["new_id"]).new_id(),
                    work_id=work_id,
                    role=assignment.role,
                    provider_id=assignment.provider_id,
                    model_id=assignment.model_id,
                    effort=assignment.effort,
                    updated_at=utcnow_iso(),
                )
            )
        await session.flush()

    await uow.write(write)
    return await get_role_models(runtime, work_id)


@router.post("/providers/test", name="test_provider_connection")
async def test_provider_connection(body: ProviderTestIn, runtime: RuntimeDep):
    return await ProviderService(runtime).test_connection(body)
