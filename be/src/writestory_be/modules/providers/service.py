from __future__ import annotations

import json

from sqlalchemy import select

from writestory_ai.providers.anthropic import AnthropicTextProvider
from writestory_ai.providers.openai_compatible import (
    OllamaTextProvider,
    OpenAICompatibleTextProvider,
)
from writestory_be.core.clock import utcnow_iso
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.core.ids import new_id
from writestory_be.infrastructure.db.models.providers import (
    Provider,
    ProviderLimit,
    ProviderModel,
)
from writestory_be.infrastructure.db.models.system import Job
from writestory_be.infrastructure.db.unit_of_work import WriteContext
from writestory_be.infrastructure.secrets.secret_store import VaultLockedError
from writestory_be.modules.providers.schemas import ModelItem, ProviderIn, ProviderPatch


def _decode(value):
    return json.loads(value) if value else None


class ProviderService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.uow = runtime.ensure_database_services()

    async def _has_key(self, provider: Provider) -> bool:
        return bool(
            provider.secret_ref
            and await self.runtime.secrets.availability(provider.secret_ref) in {"session", "vault"}
        )

    async def _out(self, row: Provider):
        return {
            "id": row.id,
            "name": row.name,
            "protocol": row.protocol,
            "base_url": row.base_url,
            "key_storage": row.key_storage,
            "has_key": await self._has_key(row),
            "auto_discover": row.auto_discover,
            "prefer_long_context": row.prefer_long_context,
            "default_effort": row.default_effort,
            "enabled": row.enabled,
            "discovery_status": row.discovery_status,
            "discovery_error": _decode(row.discovery_error),
            "discovered_at": row.discovered_at,
            "discovery_attempted_at": row.discovery_attempted_at,
            "connection_status": row.connection_status,
            "revision": row.revision,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def list(self):
        async def read(session):
            return [
                await self._out(row)
                for row in (await session.scalars(select(Provider).order_by(Provider.name))).all()
            ]

        return await self.uow.read(read)

    async def create(self, body: ProviderIn):
        now = utcnow_iso()
        row = Provider(
            id=new_id(),
            name=body.name.strip(),
            protocol=body.protocol,
            base_url=body.base_url,
            key_storage=body.key_storage,
            auto_discover=body.auto_discover,
            prefer_long_context=body.prefer_long_context,
            default_effort=body.default_effort,
            enabled=body.enabled,
            created_at=now,
            updated_at=now,
        )
        if body.api_key and body.key_storage == "none":
            raise AppError(ErrorCode.VALIDATION, detail={"field": "key_storage"})
        if body.key_storage != "none" and not body.api_key:
            raise AppError(ErrorCode.VALIDATION, detail={"field": "api_key"})
        if body.api_key:
            row.secret_ref = f"provider.{row.id}.api_key"
            await self._save_secret(
                row.secret_ref, body.api_key.get_secret_value(), body.key_storage
            )

        async def write(ctx: WriteContext):
            ctx.session.add(row)
            ctx.session.add(
                ProviderLimit(
                    provider_id=row.id,
                    max_concurrent_requests=1 if row.protocol == "ollama_lmstudio" else 4,
                    max_retries=3,
                    updated_at=now,
                )
            )
            await ctx.session.flush()
            return row

        created = await self.uow.write(write)
        await self.runtime.provider_limiter.configure(
            created.id,
            max_concurrent_requests=1 if created.protocol == "ollama_lmstudio" else 4,
        )
        return await self._out(created)

    async def patch(self, provider_id: str, body: ProviderPatch):
        async def write(ctx: WriteContext):
            row = await ctx.session.get(Provider, provider_id)
            if row is None:
                raise AppError(ErrorCode.NOT_FOUND)
            if row.revision != body.expected_revision:
                raise AppError(
                    ErrorCode.REVISION_CONFLICT, detail={"current_revision": row.revision}
                )
            values = body.model_dump(exclude_unset=True, exclude={"expected_revision", "api_key"})
            for key, value in values.items():
                if value is not None or key == "default_effort":
                    setattr(row, key, value)
            row.base_url = body.base_url if body.base_url is not None else row.base_url
            row.updated_at = utcnow_iso()
            row.revision += 1
            if body.api_key:
                storage = body.key_storage or row.key_storage
                if storage == "none":
                    raise AppError(ErrorCode.VALIDATION, detail={"field": "key_storage"})
                row.key_storage = storage
                row.secret_ref = row.secret_ref or f"provider.{row.id}.api_key"
                ctx.after_commit(
                    lambda: self._save_secret(
                        row.secret_ref, body.api_key.get_secret_value(), storage
                    )
                )
            if "base_url" in values:
                row.discovery_status = "never"
                row.discovery_error = None
            await ctx.session.flush()
            return row

        return await self._out(await self.uow.write(write))

    async def delete(self, provider_id: str):
        async def write(ctx: WriteContext):
            row = await ctx.session.get(Provider, provider_id)
            if row is None:
                raise AppError(ErrorCode.NOT_FOUND)
            jobs = (await ctx.session.scalars(select(Job).where(Job.status == "running"))).all()
            if any(provider_id in (job.pinned_json or "") for job in jobs):
                raise AppError(ErrorCode.PROVIDER_IN_USE)
            ref = row.secret_ref
            await ctx.session.delete(row)
            if ref:
                ctx.after_commit(lambda: self.runtime.secrets.delete(ref))

        await self.uow.write(write)

    async def models(self, provider_id: str):
        async def read(session):
            provider = await session.get(Provider, provider_id)
            if provider is None:
                raise AppError(ErrorCode.NOT_FOUND)
            rows = (
                await session.scalars(
                    select(ProviderModel).where(ProviderModel.provider_id == provider_id)
                )
            ).all()
            ordered = sorted((r for r in rows if r.position is not None), key=lambda r: r.position)
            active = ordered or sorted(
                (r for r in rows if r.source == "discovered" and not r.missing_since),
                key=lambda r: r.discovery_rank or 0,
            )
            others = [r for r in rows if r not in active]
            return {
                "override_active": bool(ordered),
                "default_model_id": active[0].model_id if active else None,
                "effective": [self._model_out(r) for r in active],
                "others": [self._model_out(r) for r in others],
                "revision": provider.revision,
            }

        return await self.uow.read(read)

    @staticmethod
    def _model_out(row):
        return {
            "model_id": row.model_id,
            "source": row.source,
            "display_name": row.display_name,
            "position": row.position,
            "discovery_rank": row.discovery_rank,
            "max_input_tokens": row.max_input_tokens,
            "max_tokens": row.max_tokens,
            "supported_efforts": _decode(row.supported_efforts_json),
            "capabilities": _decode(row.capabilities_json),
            "price_input_per_mtok": row.price_input_per_mtok,
            "price_output_per_mtok": row.price_output_per_mtok,
            "allowed_roles": _decode(row.allowed_roles_json),
            "missing_since": row.missing_since,
            "user_edited_fields": _decode(row.user_edited_fields_json) or [],
        }

    async def put_models(self, provider_id: str, expected_revision: int, items: list[ModelItem]):
        if len({item.model_id for item in items}) != len(items):
            raise AppError(
                ErrorCode.VALIDATION, detail={"field": "model_id", "reason": "duplicate"}
            )

        async def write(ctx: WriteContext):
            provider = await ctx.session.get(Provider, provider_id)
            if provider is None:
                raise AppError(ErrorCode.NOT_FOUND)
            if provider.revision != expected_revision:
                raise AppError(
                    ErrorCode.REVISION_CONFLICT, detail={"current_revision": provider.revision}
                )
            rows = {
                r.model_id: r
                for r in (
                    await ctx.session.scalars(
                        select(ProviderModel).where(ProviderModel.provider_id == provider_id)
                    )
                ).all()
            }
            now = utcnow_iso()
            for item in items:
                row = rows.get(item.model_id)
                if row is None:
                    row = ProviderModel(
                        id=new_id(),
                        provider_id=provider_id,
                        model_id=item.model_id,
                        source="manual",
                        first_seen_at=now,
                        updated_at=now,
                        user_edited_fields_json="[]",
                    )
                    ctx.session.add(row)
                row.position = items.index(item)
                row.source = "manual" if row.source == "manual" else row.source
                for field in (
                    "display_name",
                    "max_input_tokens",
                    "max_tokens",
                    "supported_efforts",
                    "price_input_per_mtok",
                    "price_output_per_mtok",
                    "price_cache_read_per_mtok",
                    "price_cache_write_per_mtok",
                    "allowed_roles",
                    "max_concurrent_requests",
                    "long_context_variant_model_id",
                    "long_context_params",
                    "tokens_per_syllable",
                ):
                    value = getattr(item, field, None)
                    if field in item.model_fields_set:
                        setattr(
                            row,
                            f"{field}_json"
                            if field
                            in {"supported_efforts", "allowed_roles", "long_context_params"}
                            else field,
                            json.dumps(value)
                            if field
                            in {"supported_efforts", "allowed_roles", "long_context_params"}
                            else value,
                        )
                        fields = _decode(row.user_edited_fields_json) or []
                        if field not in fields:
                            fields.append(field)
                        row.user_edited_fields_json = json.dumps(fields)
                row.updated_at = now
            keep = {item.model_id for item in items}
            for model_id, row in rows.items():
                if model_id not in keep:
                    if row.source == "manual":
                        await ctx.session.delete(row)
                    else:
                        row.position = None
            provider.revision += 1
            provider.updated_at = now
            return provider.revision

        await self.uow.write(write)
        return await self.models(provider_id)

    async def _save_secret(self, ref: str, value: str, storage: str):
        try:
            await self.runtime.secrets.put(ref, value, storage, "API key nhà cung cấp")
        except VaultLockedError as exc:
            raise AppError(ErrorCode.VAULT_LOCKED) from exc

    async def discover(self, provider_id: str):
        provider = await self.uow.read(lambda session: session.get(Provider, provider_id))
        if provider is None:
            raise AppError(ErrorCode.NOT_FOUND)
        key = None
        if provider.secret_ref:
            try:
                key = await self.runtime.secrets.get(provider.secret_ref)
            except VaultLockedError as exc:
                now = utcnow_iso()

                async def waiting(ctx):
                    row = await ctx.session.get(Provider, provider_id)
                    row.discovery_status = "waiting_vault"
                    row.discovery_attempted_at = now
                    row.discovery_error = None

                await self.uow.write(waiting)
                raise AppError(ErrorCode.VAULT_LOCKED) from exc
            except LookupError:
                key = None
        try:
            adapter = await self._adapter(provider, key)
            found = await adapter.list_models()
        except Exception as exc:
            now = utcnow_iso()
            error_code = getattr(exc, "code", "PROVIDER_UNREACHABLE")

            async def fail(ctx):
                row = await ctx.session.get(Provider, provider_id)
                row.discovery_status = "error"
                row.discovery_attempted_at = now
                row.discovery_error = json.dumps(
                    {
                        "code": error_code,
                        "message": "Không thể lấy danh sách model",
                    }
                )

            await self.uow.write(fail)
            return {
                "status": "error",
                "found": 0,
                "added": [],
                "missing": [],
                "reappeared": [],
                "error": {"code": error_code},
                "discovered_at": now,
            }
        now = utcnow_iso()
        found_by_id = {item.id: item for item in found}

        async def merge(ctx: WriteContext):
            existing = {
                r.model_id: r
                for r in (
                    await ctx.session.scalars(
                        select(ProviderModel).where(ProviderModel.provider_id == provider_id)
                    )
                ).all()
            }
            added = []
            missing = []
            reappeared = []
            for rank, item in enumerate(found):
                row = existing.get(item.id)
                if row is None:
                    ctx.session.add(
                        ProviderModel(
                            id=new_id(),
                            provider_id=provider_id,
                            model_id=item.id,
                            source="discovered",
                            discovery_rank=rank,
                            display_name=item.display_name,
                            max_input_tokens=item.max_input_tokens,
                            max_tokens=item.max_tokens,
                            supported_efforts_json=json.dumps(item.supported_efforts)
                            if item.supported_efforts is not None
                            else None,
                            capabilities_json=json.dumps(item.capabilities)
                            if item.capabilities is not None
                            else None,
                            user_edited_fields_json="[]",
                            first_seen_at=now,
                            last_seen_at=now,
                            updated_at=now,
                        )
                    )
                    added.append(item.id)
                else:
                    if row.missing_since:
                        reappeared.append(item.id)
                    row.last_seen_at = now
                    row.missing_since = None
                    row.discovery_rank = rank
                    edited = set(_decode(row.user_edited_fields_json) or [])
                    for field in (
                        "display_name",
                        "max_input_tokens",
                        "max_tokens",
                        "supported_efforts",
                    ):
                        value = getattr(item, field)
                        if field not in edited and value is not None:
                            setattr(
                                row,
                                f"{field}_json" if field == "supported_efforts" else field,
                                json.dumps(value) if field == "supported_efforts" else value,
                            )
                    row.capabilities_json = (
                        json.dumps(item.capabilities)
                        if item.capabilities is not None
                        else row.capabilities_json
                    )
            for row in existing.values():
                if row.last_seen_at and row.model_id not in found_by_id and not row.missing_since:
                    row.missing_since = now
                    missing.append(row.model_id)
            provider = await ctx.session.get(Provider, provider_id)
            provider.discovery_status = "ok"
            provider.discovery_attempted_at = now
            provider.discovered_at = now
            provider.discovery_error = None
            ctx.add_event(
                "provider.status",
                {
                    "provider_id": provider_id,
                    "discovery_status": "ok",
                    "found": len(found),
                    "added": len(added),
                    "missing": len(missing),
                    "at": now,
                },
            )
            return {
                "status": "ok",
                "found": len(found),
                "added": added,
                "missing": missing,
                "reappeared": reappeared,
                "discovered_at": now,
            }

        return await self.uow.write(merge)

    async def discover_waiting(self):
        async def read(session):
            return list(
                (
                    await session.scalars(
                        select(Provider.id).where(
                            Provider.enabled.is_(True), Provider.discovery_status == "waiting_vault"
                        )
                    )
                ).all()
            )

        for provider_id in await self.uow.read(read):
            self.runtime.spawn(self.discover(provider_id))

    async def test_connection(self, body):
        from time import perf_counter

        if body.provider_id:
            started = perf_counter()
            result = await self.discover(body.provider_id)
            return {
                "ok": result["status"] == "ok",
                "latency_ms": round((perf_counter() - started) * 1000),
                "model_count": result["found"],
                "called_model": body.model_id,
                "error": result.get("error"),
            }
        if not body.protocol or not body.base_url:
            raise AppError(
                ErrorCode.VALIDATION, detail={"reason": "provider_or_connection_required"}
            )
        from types import SimpleNamespace

        started = perf_counter()
        draft = SimpleNamespace(protocol=body.protocol, base_url=body.base_url.rstrip("/"))
        try:
            adapter = await self._adapter(
                draft, body.api_key.get_secret_value() if body.api_key else None
            )
            models = await adapter.list_models()
            return {
                "ok": True,
                "latency_ms": round((perf_counter() - started) * 1000),
                "model_count": len(models),
                "called_model": body.model_id,
                "error": None,
            }
        except Exception as exc:
            return {
                "ok": False,
                "latency_ms": round((perf_counter() - started) * 1000),
                "model_count": None,
                "called_model": body.model_id,
                "error": {"code": getattr(exc, "code", "PROVIDER_UNREACHABLE")},
            }

    async def _adapter(self, provider, key):
        if provider.protocol == "anthropic":
            return AnthropicTextProvider(key or "", base_url=provider.base_url, timeout=10)
        if provider.protocol == "ollama_lmstudio":
            return OllamaTextProvider(base_url=provider.base_url, api_key=key, timeout=10)
        return OpenAICompatibleTextProvider(base_url=provider.base_url, api_key=key, timeout=10)
