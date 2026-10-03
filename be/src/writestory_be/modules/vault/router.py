from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request, Response

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.secrets.secret_store import SECRET_REF_PATTERN
from writestory_be.infrastructure.secrets.vault import VaultCorrupt, VaultPasswordInvalid
from writestory_be.modules.vault.schemas import (
    ChangePasswordRequest,
    CreateVaultRequest,
    PutSecretRequest,
    ResetVaultRequest,
    SecretInfo,
    UnlockRequest,
    VaultModeRequest,
    VaultStatus,
)
from writestory_be.modules.vault.service import VaultApiService

router = APIRouter(prefix="/v1", tags=["vault"])


def _app_error(code: ErrorCode, *, status: int | None = None, detail=None, headers=None):
    return AppError(code, status=status, detail=detail, headers=headers)


def _document(runtime) -> dict[str, Any] | None:
    if not runtime.vault.file.exists():
        return None
    try:
        return runtime.vault.file.read()
    except VaultCorrupt:
        raise _app_error(ErrorCode.VAULT_CORRUPT) from None


async def _status(runtime, throttle_ms: int = 0) -> VaultStatus:
    settings = await runtime.vault_settings_store.read()
    doc = _document(runtime)
    if not throttle_ms:
        retry_remaining = getattr(runtime, "vault_retry_at", 0.0) - time.monotonic()
        throttle_ms = max(0, int(retry_remaining * 1000))
    return VaultStatus(
        state=runtime.vault.state,
        mode=settings.mode,
        kdf=doc["kdf"]["name"] if doc else None,
        created_at=doc.get("created_at") if doc else None,
        updated_at=doc.get("updated_at") if doc else None,
        waiting_jobs=await runtime.vault_settings_store.waiting_jobs(),
        throttle_ms=throttle_ms,
        revision=settings.revision,
    )


async def _publish(runtime) -> None:
    status = await _status(runtime)
    runtime.event_bus.publish("vault.status", {"state": status.state, "mode": status.mode})


def _vault_exception(exc: Exception):
    if isinstance(exc, VaultPasswordInvalid):
        return _app_error(ErrorCode.VAULT_PASSWORD_INVALID)
    if isinstance(exc, VaultCorrupt):
        detail = {"reason": exc.reason} if exc.reason else None
        return _app_error(ErrorCode.VAULT_CORRUPT, detail=detail)
    return _app_error(ErrorCode.INTERNAL)


@router.get("/vault/status", response_model=VaultStatus)
async def status(runtime: RuntimeDep):
    return await _status(runtime)


@router.post("/vault", status_code=201, response_model=VaultStatus)
async def create_vault(body: CreateVaultRequest, runtime: RuntimeDep):
    try:
        await runtime.vault.create(
            body.password.get_secret_value(), body.password_confirm.get_secret_value()
        )
    except FileExistsError as exc:
        raise _app_error(ErrorCode.VAULT_ALREADY_EXISTS) from exc
    except ValueError as exc:
        raise _app_error(ErrorCode.VALIDATION, detail={"reason": "password_confirmation"}) from exc
    except (VaultCorrupt, VaultPasswordInvalid) as exc:
        raise _vault_exception(exc) from exc
    await runtime.vault_settings_store.set_mode_value("vault")
    if body.import_session_secrets:
        for ref in runtime.session_secrets.refs():
            item = runtime.session_secrets.get(ref)
            if item:
                await runtime.secrets.put(ref, item["value"], "vault", item.get("label"))
                runtime.session_secrets.delete(ref)
        state = await runtime.vault_settings_store.read()
        index = dict(state.index or {})
        for ref in await runtime.vault.refs():
            entry = await runtime.vault.get(ref)
            if entry:
                index[ref] = {
                    "storage": "vault",
                    "label": entry.get("label"),
                    "updated_at": entry.get("updated_at"),
                }
        await runtime.vault_settings_store.set_index(index)
    await runtime.secrets.vault_unlocked()
    if runtime.uow is not None:
        from writestory_be.modules.providers.service import ProviderService

        runtime.spawn(ProviderService(runtime).discover_waiting())
    await _publish(runtime)
    return await _status(runtime)


@router.post("/vault/unlock", response_model=VaultStatus)
async def unlock(body: UnlockRequest, runtime: RuntimeDep):
    api_service = VaultApiService(runtime)
    api_service.check_throttle()
    if not runtime.vault.file.exists():
        raise _app_error(ErrorCode.VAULT_NOT_FOUND)
    try:
        await runtime.vault.unlock(body.password.get_secret_value())
    except (VaultCorrupt, VaultPasswordInvalid) as exc:
        if isinstance(exc, VaultPasswordInvalid):
            api_service.record_password_failure()
        raise _vault_exception(exc) from exc
    api_service.clear_password_failures()
    await runtime.secrets.vault_unlocked()
    if runtime.uow is not None:
        from writestory_be.modules.providers.service import ProviderService

        runtime.spawn(ProviderService(runtime).discover_waiting())
    vault_refs = await runtime.vault.refs()
    index = {}
    for ref in vault_refs:
        entry = await runtime.vault.get(ref) or {}
        index[ref] = {
            "storage": "vault",
            "label": entry.get("label"),
            "updated_at": entry.get("updated_at"),
        }
    await runtime.vault_settings_store.set_index(index)
    await _publish(runtime)
    return await _status(runtime)


@router.post("/vault/lock", response_model=VaultStatus)
async def lock(runtime: RuntimeDep):
    await runtime.vault.lock()
    await runtime.secrets.vault_locked()
    await _publish(runtime)
    return await _status(runtime)


@router.post("/vault/change-password", response_model=VaultStatus)
async def change_password(body: ChangePasswordRequest, runtime: RuntimeDep):
    api_service = VaultApiService(runtime)
    api_service.check_throttle()
    try:
        await runtime.vault.change_password(
            body.current_password.get_secret_value(),
            body.new_password.get_secret_value(),
            body.new_password_confirm.get_secret_value(),
        )
    except (VaultCorrupt, VaultPasswordInvalid) as exc:
        if isinstance(exc, VaultPasswordInvalid):
            api_service.record_password_failure()
        raise _vault_exception(exc) from exc
    except ValueError as exc:
        raise _app_error(ErrorCode.VALIDATION, detail={"reason": "password_confirmation"}) from exc
    api_service.clear_password_failures()
    await _publish(runtime)
    return await _status(runtime)


@router.post("/vault/reset", response_model=VaultStatus)
async def reset(body: ResetVaultRequest, request: Request, runtime: RuntimeDep):
    if not request.headers.get("Idempotency-Key", "").strip():
        raise _app_error(ErrorCode.VALIDATION, detail={"field": "Idempotency-Key"})
    if body.confirm != "XÓA VAULT":
        raise _app_error(ErrorCode.VALIDATION, detail={"reason": "confirmation"})
    await runtime.vault.lock()
    runtime.vault.file.path.unlink(missing_ok=True)
    await runtime.vault_settings_store.set_mode_value("undecided")
    await runtime.vault_settings_store.set_index({})
    runtime.secrets._vault_refs.clear()
    await _publish(runtime)
    return await _status(runtime)


@router.put("/vault/mode", response_model=VaultStatus)
async def set_mode(body: VaultModeRequest, runtime: RuntimeDep):
    if body.mode == "vault" and not runtime.vault.file.exists():
        raise _app_error(ErrorCode.VALIDATION, detail={"reason": "vault_absent"})
    changed = await runtime.vault_settings_store.set_mode(body.mode, body.expected_revision)
    if not changed:
        raise _app_error(ErrorCode.REVISION_CONFLICT)
    await _publish(runtime)
    return await _status(runtime)


@router.get("/secrets", response_model=list[SecretInfo])
async def list_secrets(runtime: RuntimeDep):
    settings = await runtime.vault_settings_store.read()
    index = settings.index or {}
    runtime.secrets.remember_vault_refs(set(index))
    infos = []
    for ref, metadata in index.items():
        infos.append(SecretInfo(ref=ref, available=runtime.vault.state == "unlocked", **metadata))
    for ref in runtime.session_secrets.refs():
        item = runtime.session_secrets.get(ref) or {}
        infos.append(
            SecretInfo(ref=ref, storage="session", available=True, label=item.get("label"))
        )
    return infos


@router.put("/secrets/{ref}", response_model=SecretInfo)
async def put_secret(ref: str, body: PutSecretRequest, runtime: RuntimeDep):
    if not SECRET_REF_PATTERN.fullmatch(ref):
        raise _app_error(ErrorCode.VALIDATION, detail={"reason": "secret_ref"})
    try:
        await runtime.secrets.put(ref, body.value.get_secret_value(), body.storage, body.label)
    except PermissionError as exc:
        if body.storage == "vault" and runtime.vault.state == "absent":
            raise _app_error(ErrorCode.VALIDATION, detail={"reason": "vault_absent"}) from exc
        raise _app_error(ErrorCode.VAULT_LOCKED) from exc
    if body.storage == "vault":
        state = await runtime.vault_settings_store.read()
        index = dict(state.index or {})
        entry = await runtime.vault.get(ref)
        index[ref] = {
            "storage": "vault",
            "label": body.label,
            "updated_at": entry.get("updated_at") if entry else None,
        }
        await runtime.vault_settings_store.set_index(index)
    return SecretInfo(ref=ref, storage=body.storage, available=True, label=body.label)


@router.delete("/secrets/{ref}", status_code=204)
async def delete_secret(ref: str, runtime: RuntimeDep):
    if not SECRET_REF_PATTERN.fullmatch(ref):
        raise _app_error(ErrorCode.VALIDATION, detail={"reason": "secret_ref"})
    state = await runtime.vault_settings_store.read()
    runtime.secrets.remember_vault_refs(set(state.index or {}))
    try:
        await runtime.secrets.delete(ref)
    except PermissionError as exc:
        raise _app_error(ErrorCode.VAULT_LOCKED) from exc
    index = dict(state.index or {})
    index.pop(ref, None)
    await runtime.vault_settings_store.set_index(index)
    return Response(status_code=204)
