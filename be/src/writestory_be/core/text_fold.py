import unicodedata


def fold_text(value: str) -> str:
    """NFC, lowercase, strip Vietnamese diacritics, and fold đ to d for search."""
    normalized = unicodedata.normalize("NFC", value).casefold().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", normalized)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
