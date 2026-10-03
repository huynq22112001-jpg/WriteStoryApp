import unicodedata

from writestory_be.core.text_fold import fold_text


def test_fold_vietnamese_and_nfd():
    assert fold_text("Nguyễn") == "nguyen"
    assert fold_text("Đường") == "duong"
    assert fold_text(unicodedata.normalize("NFD", "Nguyễn")) == "nguyen"
