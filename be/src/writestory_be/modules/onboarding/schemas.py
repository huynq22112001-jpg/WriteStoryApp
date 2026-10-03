from typing import Literal

from pydantic import BaseModel, Field

OnboardingStep = Literal["security", "provider", "first_work"]
StepStatus = Literal["done", "pending", "skipped", "not_applicable"]


class OnboardingSteps(BaseModel):
    data_root: Literal["done", "not_applicable"]
    security: StepStatus
    provider: StepStatus
    first_work: StepStatus


class OnboardingState(BaseModel):
    status: Literal["pending", "completed", "skipped"]
    step: OnboardingStep | None
    revision: int = Field(ge=1)
    steps: OnboardingSteps
    platform: str
    completed_at: str | None = None


class UpdateOnboardingRequest(BaseModel):
    step: OnboardingStep
    expected_revision: int = Field(ge=1)


class CompleteOnboardingRequest(BaseModel):
    skipped: bool = False
