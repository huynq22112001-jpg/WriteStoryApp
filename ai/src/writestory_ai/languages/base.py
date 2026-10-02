from typing import Protocol


class LanguagePack(Protocol):
    """Mọi xử lý phụ thuộc ngôn ngữ nằm sau interface này (Plan §6.6).

    Pipeline không chứa logic riêng của một ngôn ngữ; thêm ngôn ngữ = thêm gói mới.
    Các thành phần còn lại (deterministic checks, prompts, methods, slop list, genre presets)
    được bổ sung ở F08.
    """

    code: str
    length_unit: str

    def normalize(self, text: str) -> str:
        """Chuẩn hóa văn bản trước khi lưu/so sánh."""
        ...

    def count_length(self, text: str) -> int:
        """Đếm độ dài theo đơn vị của ngôn ngữ (tiếng Việt: âm tiết)."""
        ...

    def search_fold(self, text: str) -> str:
        """Chuẩn hóa cho cột tìm kiếm FTS và câu truy vấn."""
        ...
