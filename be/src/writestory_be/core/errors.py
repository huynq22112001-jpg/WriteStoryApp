"""Hợp đồng lỗi dùng chung (Plan §23.1.D, F01 be.md §B).

Tính năng mới thêm mã phải đăng ký vào `ErrorCode` và các bảng bên dưới.
"""

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    VALIDATION = "VALIDATION"
    REVISION_CONFLICT = "REVISION_CONFLICT"
    WORK_BLOCKED = "WORK_BLOCKED"
    WORK_BUSY_QUEUED = "WORK_BUSY_QUEUED"
    CHAPTER_RANGE_CONFLICT = "CHAPTER_RANGE_CONFLICT"
    VAULT_LOCKED = "VAULT_LOCKED"
    VAULT_PASSWORD_INVALID = "VAULT_PASSWORD_INVALID"
    VAULT_UNLOCK_THROTTLED = "VAULT_UNLOCK_THROTTLED"
    VAULT_ALREADY_EXISTS = "VAULT_ALREADY_EXISTS"
    VAULT_NOT_FOUND = "VAULT_NOT_FOUND"
    VAULT_CORRUPT = "VAULT_CORRUPT"
    SECRET_MISSING = "SECRET_MISSING"
    PROVIDER_AUTH = "PROVIDER_AUTH"
    PROVIDER_UNREACHABLE = "PROVIDER_UNREACHABLE"
    PROVIDER_SERVER_ERROR = "PROVIDER_SERVER_ERROR"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_REFUSAL = "PROVIDER_REFUSAL"
    OUTPUT_TRUNCATED = "OUTPUT_TRUNCATED"
    STRUCTURED_OUTPUT_INVALID = "STRUCTURED_OUTPUT_INVALID"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN_HOST = "FORBIDDEN_HOST"
    FORBIDDEN_ORIGIN = "FORBIDDEN_ORIGIN"
    NOT_FOUND = "NOT_FOUND"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    DB_BUSY = "DB_BUSY"
    BACKEND_SHUTTING_DOWN = "BACKEND_SHUTTING_DOWN"
    INTERNAL = "INTERNAL"


class ErrorAction(StrEnum):
    RETRY = "retry"
    RELOAD = "reload"
    WAIT = "wait"
    VIEW_DIFF = "view_diff"
    OPEN_RESYNC = "open_resync"
    UNLOCK_VAULT = "unlock_vault"
    OPEN_PROVIDER_SETTINGS = "open_provider_settings"
    EDIT_INSTRUCTION = "edit_instruction"
    CHANGE_MODEL = "change_model"
    ADJUST_BUDGET = "adjust_budget"


# (HTTP status, retryable, action mặc định, thông điệp dự phòng tiếng Việt).
# FE ưu tiên chuỗi i18n theo `code`; `message` chỉ là bản dự phòng (Plan §23.1.D).
_SPEC: dict[ErrorCode, tuple[int, bool, ErrorAction | None, str]] = {
    ErrorCode.VALIDATION: (422, False, None, "Dữ liệu gửi lên không hợp lệ."),
    ErrorCode.REVISION_CONFLICT: (
        409, False, ErrorAction.VIEW_DIFF, "Nội dung đã thay đổi ở nơi khác; hãy xem so sánh."
    ),
    ErrorCode.WORK_BLOCKED: (
        409,
        False,
        ErrorAction.OPEN_RESYNC,
        "Mạch truyện đang bị chặn, cần xử lý trước khi viết tiếp.",
    ),
    ErrorCode.WORK_BUSY_QUEUED: (
        409,
        True,
        ErrorAction.WAIT,
        "Truyện đang có tác vụ khác; đã xếp hàng.",
    ),
    ErrorCode.CHAPTER_RANGE_CONFLICT: (
        409, False, None, "Không thể thay đổi thứ tự chương khi truyện đang chạy."
    ),
    ErrorCode.VAULT_LOCKED: (423, True, ErrorAction.UNLOCK_VAULT, "Kho khóa API đang khóa."),
    ErrorCode.VAULT_PASSWORD_INVALID: (422, False, None, "Mật khẩu vault không đúng."),
    ErrorCode.VAULT_UNLOCK_THROTTLED: (429, True, ErrorAction.WAIT, "Thử mở vault quá nhiều lần."),
    ErrorCode.VAULT_ALREADY_EXISTS: (409, False, None, "Vault đã tồn tại."),
    ErrorCode.VAULT_NOT_FOUND: (404, False, None, "Chưa có vault."),
    ErrorCode.VAULT_CORRUPT: (500, False, ErrorAction.RELOAD, "Không thể đọc vault."),
    ErrorCode.SECRET_MISSING: (409, False, ErrorAction.OPEN_PROVIDER_SETTINGS, "Chưa lưu API key."),
    ErrorCode.PROVIDER_AUTH: (
        502, False, ErrorAction.OPEN_PROVIDER_SETTINGS, "Nhà cung cấp AI từ chối API key."
    ),
    ErrorCode.PROVIDER_UNREACHABLE: (
        503, True, ErrorAction.RETRY, "Không kết nối được tới nhà cung cấp AI."
    ),
    ErrorCode.PROVIDER_SERVER_ERROR: (
        502, True, ErrorAction.RETRY, "Nhà cung cấp AI gặp lỗi máy chủ."
    ),
    ErrorCode.PROVIDER_RATE_LIMIT: (
        429,
        True,
        ErrorAction.WAIT,
        "Nhà cung cấp AI đang giới hạn tốc độ.",
    ),
    ErrorCode.PROVIDER_REFUSAL: (
        422, False, ErrorAction.EDIT_INSTRUCTION, "Model từ chối viết nội dung này."
    ),
    ErrorCode.OUTPUT_TRUNCATED: (422, True, ErrorAction.RETRY, "Kết quả AI bị cắt giữa chừng."),
    ErrorCode.STRUCTURED_OUTPUT_INVALID: (
        422, True, ErrorAction.CHANGE_MODEL, "Kết quả AI không đúng định dạng."
    ),
    ErrorCode.BUDGET_EXCEEDED: (409, False, ErrorAction.ADJUST_BUDGET, "Đã vượt ngân sách."),
    ErrorCode.UNAUTHORIZED: (401, False, ErrorAction.RELOAD, "Phiên làm việc không hợp lệ."),
    ErrorCode.FORBIDDEN_HOST: (400, False, None, "Yêu cầu không hợp lệ."),
    ErrorCode.FORBIDDEN_ORIGIN: (403, False, None, "Nguồn gọi không được phép."),
    ErrorCode.NOT_FOUND: (404, False, None, "Không tìm thấy."),
    ErrorCode.IDEMPOTENCY_CONFLICT: (409, False, None, "Thao tác trùng khóa nhưng nội dung khác."),
    ErrorCode.DB_BUSY: (503, True, ErrorAction.RETRY, "Cơ sở dữ liệu đang bận."),
    ErrorCode.BACKEND_SHUTTING_DOWN: (503, False, None, "Ứng dụng đang tắt."),
    ErrorCode.INTERNAL: (500, False, ErrorAction.RELOAD, "Đã có lỗi không mong muốn."),
}

assert set(_SPEC) == set(ErrorCode), "Mỗi ErrorCode phải có cấu hình trong _SPEC"


def http_status(code: ErrorCode) -> int:
    return _SPEC[code][0]


def default_retryable(code: ErrorCode) -> bool:
    return _SPEC[code][1]


def default_action(code: ErrorCode) -> ErrorAction | None:
    return _SPEC[code][2]


def default_message(code: ErrorCode) -> str:
    return _SPEC[code][3]


class AppError(Exception):
    """Lỗi nghiệp vụ có mã; exception handler chuyển thành `ErrorResponse`."""

    def __init__(
        self,
        code: ErrorCode,
        *,
        detail: dict[str, Any] | None = None,
        message: str | None = None,
        status: int | None = None,
        retryable: bool | None = None,
        action: ErrorAction | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.detail = detail
        self.message = message or default_message(code)
        self.status = status or http_status(code)
        self.retryable = default_retryable(code) if retryable is None else retryable
        self.action = default_action(code) if action is None else action
        self.headers = headers
        super().__init__(f"{code}: {self.message}")
