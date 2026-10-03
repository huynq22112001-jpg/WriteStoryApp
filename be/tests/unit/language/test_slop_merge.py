import pytest

from writestory_be.core.errors import AppError
from writestory_be.modules.language.domain import merge_slop_entries, validate_slop_entries


def test_slop_merge_obeys_builtin_app_work_precedence():
    builtin = [
        type(
            "Entry",
            (),
            {
                "id": "keep",
                "pattern": "cụm",
                "is_regex": False,
                "scope": "anywhere",
                "max_per_1000_units": None,
                "note": "",
            },
        )(),
        type(
            "Entry",
            (),
            {
                "id": "disabled",
                "pattern": "bỏ",
                "is_regex": False,
                "scope": "anywhere",
                "max_per_1000_units": None,
                "note": "",
            },
        )(),
    ]
    result = merge_slop_entries(
        builtin,
        {
            "disabled": ["disabled"],
            "additions": [{"id": "app", "pattern": "thêm", "is_regex": False}],
        },
        [],
        ["truyện"],
    )
    assert [entry["id"] for entry in result] == ["keep", "app", "work:0"]


@pytest.mark.parametrize("pattern", ["(", r"(a+)+$", r"(a)\1", r"(?<=a)b"])
def test_slop_rejects_invalid_or_dangerous_regex(pattern):
    with pytest.raises(AppError):
        validate_slop_entries([{"id": "custom", "pattern": pattern, "is_regex": True}])


def test_slop_accepts_bounded_simple_regex():
    validate_slop_entries([{"id": "custom", "pattern": r"\bthật sự\b", "is_regex": True}])
