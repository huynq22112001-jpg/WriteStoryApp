from writestory_ai.languages.vi.length import count_syllables
from writestory_ai.languages.vi.normalizer import normalize_text
from writestory_ai.languages.vi.search import search_fold


class VietnamesePack:
    code = "vi"
    length_unit = "syllable"

    def normalize(self, text: str) -> str:
        return normalize_text(text)

    def count_length(self, text: str) -> int:
        return count_syllables(text)

    def search_fold(self, text: str) -> str:
        return search_fold(text)


__all__ = ["VietnamesePack", "count_syllables", "normalize_text", "search_fold"]
