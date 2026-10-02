import unicodedata


def _has_word_char(token: str) -> bool:
    return any(unicodedata.category(ch)[0] in ("L", "N") for ch in token)


def count_syllables(text: str) -> int:
    """Đếm âm tiết tiếng Việt (Plan §6.6 "Đo độ dài").

    Chuẩn hóa NFC, tách theo khoảng trắng, bỏ các token chỉ gồm dấu câu
    (ví dụ "—", "…", "\"" đứng riêng). Số viết liền ("10.000") tính là một.
    """
    text = unicodedata.normalize("NFC", text)
    return sum(1 for token in text.split() if _has_word_char(token))
