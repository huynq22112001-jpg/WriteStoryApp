import unicodedata

_D_MAP = str.maketrans({"đ": "d", "Đ": "D"})


def search_fold(text: str) -> str:
    """Chuẩn hóa cho tìm kiếm không dấu (Plan §5, đã chạy thử trên SQLite 3.51.3).

    FTS5 `unicode61 remove_diacritics 2` bỏ được dấu của chữ hai dấu (ộ, ễ) nhưng **không**
    gập `đ→d` (U+0111 không có phân rã Unicode). Hàm này làm cả hai ở tầng app để cột tìm kiếm
    và câu truy vấn được chuẩn hóa giống nhau.
    """
    decomposed = unicodedata.normalize("NFD", text.translate(_D_MAP))
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", stripped).casefold()
