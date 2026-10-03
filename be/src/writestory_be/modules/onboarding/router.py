from fastapi import APIRouter

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.modules.onboarding.schemas import (
    CompleteOnboardingRequest,
    OnboardingState,
    UpdateOnboardingRequest,
)
from writestory_be.modules.onboarding.service import OnboardingService

router = APIRouter(prefix="/v1/onboarding", tags=["onboarding"])


def _service(runtime) -> OnboardingService:
    return OnboardingService(runtime.data_root / "db" / "app.sqlite3", runtime.vault_settings_store)


async def _state(runtime) -> OnboardingState:
    await runtime.vault_settings_store.read()
    return await _service(runtime).get()


@router.get("", response_model=OnboardingState)
async def get_onboarding(runtime: RuntimeDep):
    return await _state(runtime)


@router.put("", response_model=OnboardingState)
async def update_onboarding(body: UpdateOnboardingRequest, runtime: RuntimeDep):
    if not await _service(runtime).update_step(body.step, body.expected_revision):
        raise AppError(ErrorCode.REVISION_CONFLICT)
    return await _state(runtime)


@router.post("/complete", response_model=OnboardingState)
async def complete_onboarding(body: CompleteOnboardingRequest, runtime: RuntimeDep):
    await _service(runtime).complete(body.skipped)
    return await _state(runtime)
