from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from sqlalchemy import or_, select

from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.db.models.providers import Provider, ProviderModel, RoleModel


@dataclass(frozen=True)
class PinnedModelConfig:
    provider_id: str
    model_id: str
    request_model_id: str
    effort: str | None
    max_input_tokens: int | None
    max_tokens: int | None
    extra_params: dict
    prices: dict
    notes: tuple[str, ...]
    resolved_at: str

    def to_dict(self):
        return asdict(self)


class ModelResolver:
    def __init__(self, runtime):
        self.runtime = runtime
        self.uow = runtime.ensure_database_services()

    async def resolve(self, work_id: str | None, role: str):
        async def read(session):
            query = select(RoleModel).where(RoleModel.role == role)
            if work_id:
                query = query.where(or_(RoleModel.work_id == work_id, RoleModel.work_id.is_(None)))
            else:
                query = query.where(RoleModel.work_id.is_(None))
            assignments = (await session.scalars(query)).all()
            choices = {item.work_id: item for item in assignments}
            work_assignment = choices.get(work_id)
            app_assignment = choices.get(None)
            selected = work_assignment or app_assignment
            providers = (
                await session.scalars(
                    select(Provider).where(Provider.enabled.is_(True)).order_by(Provider.created_at)
                )
            ).all()
            if selected and selected.provider_id:
                providers.sort(key=lambda p: p.id != selected.provider_id)
            for provider in providers:
                model_rows = (
                    await session.scalars(
                        select(ProviderModel).where(ProviderModel.provider_id == provider.id)
                    )
                ).all()
                ordered = sorted(
                    (m for m in model_rows if m.position is not None), key=lambda m: m.position
                )
                candidates = ordered or sorted(
                    (m for m in model_rows if m.source == "discovered" and m.missing_since is None),
                    key=lambda m: m.discovery_rank or 0,
                )
                if selected and selected.model_id:
                    candidates = [m for m in candidates if m.model_id == selected.model_id]
                for model in candidates:
                    allowed = (
                        json.loads(model.allowed_roles_json) if model.allowed_roles_json else None
                    )
                    if allowed and role not in allowed:
                        continue
                    efforts = (
                        json.loads(model.supported_efforts_json)
                        if model.supported_efforts_json
                        else None
                    )
                    effort = (
                        (work_assignment.effort if work_assignment else None)
                        or (app_assignment.effort if app_assignment else None)
                        or provider.default_effort
                    )
                    notes = []
                    if effort and efforts is not None and effort not in efforts:
                        effort = None
                        notes.append("effort_dropped_unsupported")
                    if model.missing_since:
                        notes.append("model_missing_on_server")
                    model_id = model.model_id
                    request_model_id = model_id
                    params = {}
                    if (
                        not selected
                        and provider.prefer_long_context
                        and model.long_context_variant_model_id
                    ):
                        request_model_id = model.long_context_variant_model_id
                        params = json.loads(model.long_context_params_json or "{}")
                    return PinnedModelConfig(
                        provider_id=provider.id,
                        model_id=model_id,
                        request_model_id=request_model_id,
                        effort=effort,
                        max_input_tokens=model.max_input_tokens,
                        max_tokens=model.max_tokens,
                        extra_params=params,
                        prices={
                            "input": model.price_input_per_mtok,
                            "output": model.price_output_per_mtok,
                        },
                        notes=tuple(notes),
                        resolved_at=__import__(
                            "writestory_be.core.clock", fromlist=["utcnow_iso"]
                        ).utcnow_iso(),
                    ).to_dict()
            raise AppError(
                ErrorCode.VALIDATION, detail={"reason": "no_model_for_role", "role": role}
            )

        return await self.uow.read(read)
