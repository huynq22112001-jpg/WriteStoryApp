"""Lỗi có kiểu của package AI.

`code` trùng giá trị `ErrorCode` của BE (Plan §23.1.D) để BE chuyển thẳng sang hợp đồng lỗi
API hoặc `jobs.wait_reason` mà không cần bảng ánh xạ riêng.
"""


class AIError(Exception):
    code: str = "INTERNAL"
    retryable: bool = False

    def __init__(self, message: str = "", *, detail: dict | None = None) -> None:
        super().__init__(message or self.code)
        self.detail = detail or {}


class ProviderAuthError(AIError):
    code = "PROVIDER_AUTH"


class ProviderUnreachableError(AIError):
    code = "PROVIDER_UNREACHABLE"
    retryable = True


class ProviderRateLimitError(AIError):
    code = "PROVIDER_RATE_LIMIT"
    retryable = True

    def __init__(self, message: str = "", *, retry_after: float | None = None) -> None:
        super().__init__(message, detail={"retry_after": retry_after})
        self.retry_after = retry_after


class ProviderServerError(AIError):
    code = "PROVIDER_SERVER_ERROR"
    retryable = True


class ProviderRefusalError(AIError):
    code = "PROVIDER_REFUSAL"


class OutputTruncatedError(AIError):
    code = "OUTPUT_TRUNCATED"
    retryable = True


class StructuredOutputInvalidError(AIError):
    code = "STRUCTURED_OUTPUT_INVALID"
    retryable = True


class OutputEmptyError(AIError):
    code = "OUTPUT_EMPTY"
    retryable = True


class CancelledError(AIError):
    code = "CANCELLED"
