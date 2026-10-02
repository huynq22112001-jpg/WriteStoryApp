import unicodedata

import pytest

from writestory_ai.languages.registry import (
    UnsupportedLanguageError,
    get_language_pack,
)
from writestory_ai.languages.vi import count_syllables, normalize_text, search_fold


class TestCountSyllables:
    def test_counts_space_separated_syllables(self):
        assert count_syllables("Lâm Phong siết chặt chuôi kiếm") == 6

    def test_ignores_standalone_punctuation(self):
        # Đi, thôi!, hắn, nói, rồi, bước, ra. → 7; "—" và "…" đứng riêng không tính.
        assert count_syllables("— Đi thôi! — hắn nói … rồi bước ra.") == 7

    def test_nfd_input_counts_same_as_nfc(self):
        text = "Nguyễn Văn Ộc người ơi"
        assert count_syllables(unicodedata.normalize("NFD", text)) == count_syllables(text) == 5

    def test_number_is_one_unit(self):
        assert count_syllables("Có 10.000 binh mã") == 4

    def test_empty(self):
        assert count_syllables("  \n\t ") == 0


class TestSearchFold:
    # Khớp kết quả FTS đã chạy thử (tests/flows/T13): sau fold, truy vấn không dấu phải khớp.
    @pytest.mark.parametrize(
        ("original", "query"),
        [
            ("Nguyễn", "nguyen"),
            ("Ộc", "oc"),
            ("người", "nguoi"),
            ("Đường", "duong"),  # FTS5 không gập đ→d; tầng app phải làm
            ("đi", "di"),
            ("ơi", "oi"),
        ],
    )
    def test_folds_to_ascii_query(self, original, query):
        assert search_fold(original) == search_fold(query) == query

    def test_nfd_and_nfc_fold_equal(self):
        s = "Đường đi Nguyễn Văn Ộc"
        assert search_fold(unicodedata.normalize("NFD", s)) == search_fold(s)


class TestNormalize:
    def test_converts_to_nfc(self):
        nfd = unicodedata.normalize("NFD", "Thủy Mặc")
        assert normalize_text(nfd) == "Thủy Mặc"
        assert unicodedata.is_normalized("NFC", normalize_text(nfd))

    def test_line_endings_and_special_spaces(self):
        raw = "Dòng một\u00a0có NBSP  \r\nDòng\u200b hai\r"
        assert normalize_text(raw) == "Dòng một có NBSP\nDòng hai\n"

    def test_keeps_tone_mark_style(self):
        # Không tự đổi hoà ↔ hòa (thuộc style_profile, F08).
        assert normalize_text("hoà") == "hoà"
        assert normalize_text("hòa") == "hòa"


class TestRegistry:
    def test_vi_pack(self):
        pack = get_language_pack("vi")
        assert pack.code == "vi"
        assert pack.length_unit == "syllable"
        assert pack.count_length("một hai ba") == 3

    def test_unsupported_language(self):
        with pytest.raises(UnsupportedLanguageError):
            get_language_pack("en")
