from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LanguagePack(Protocol):
    """Mọi xử lý phụ thuộc ngôn ngữ nằm sau interface này (Plan §6.6).

    Pipeline không chứa logic riêng của một ngôn ngữ; thêm ngôn ngữ = thêm gói mới.
    Các thành phần còn lại (deterministic checks, prompts, methods, slop list, genre presets)
    được bổ sung ở F08.
    """

    code: str
    length_unit: str
    deterministic_checks: list[Any]
    slop_list: list[Any]
    genre_presets: dict[str, Any]
    prompts_dir: Path

    def normalize(self, text: str) -> str:
        """Chuẩn hóa văn bản trước khi lưu/so sánh."""
        ...

    def count_length(self, text: str) -> int:
        """Đếm độ dài theo đơn vị của ngôn ngữ (tiếng Việt: âm tiết)."""
        ...

    def search_fold(self, text: str) -> str:
        """Chuẩn hóa cho cột tìm kiếm FTS và câu truy vấn."""
        ...


class LanguageFindingModel(Protocol):
    check_id: str
    kind: str
    severity: str
    confidence: str
    paragraph_id: str | None
    start: int | None
    end: int | None
    quote: str
    message_key: str
    params: dict[str, Any]
    suggestion: str | None
    needs_confirmation: bool


class CheckContextModel(Protocol):
    work_id: str
    chapter_no: int
    genre_preset: Any
    profile: Any
    paragraphs: list[Any]
