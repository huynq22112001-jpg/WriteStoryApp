import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from writestory_ai.languages.vi.length import count_syllables
from writestory_ai.languages.vi.normalizer import normalize_text
from writestory_ai.languages.vi.search import search_fold


@dataclass(frozen=True)
class SlopEntry:
    id: str
    pattern: str
    is_regex: bool
    scope: str
    max_per_1000_units: float | None
    note: str


def _read_data(name: str) -> str:
    return files("writestory_ai.languages.vi").joinpath("data", name).read_text(encoding="utf-8")


class VietnamesePack:
    code = "vi"
    length_unit = "syllable"
    prompts_dir = Path(__file__).parent / "prompts"
    deterministic_checks: ClassVar[list] = []
    pronouns = json.loads(_read_data("pronouns.json"))["terms"]
    speech_verbs = tuple(
        line.strip() for line in _read_data("speech_verbs.txt").splitlines() if line.strip()
    )
    han_viet_terms = tuple(
        line.strip()
        for line in _read_data("han_viet_common.txt").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    anachronisms = tuple(
        line.strip()
        for line in files("writestory_ai.languages.vi")
        .joinpath("data", "anachronisms", "co_trang.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    foreign_allowlist = frozenset(
        line.strip().casefold()
        for line in _read_data("foreign_allowlist.txt").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    hoi_nga_pairs: ClassVar[dict[str, str]] = dict(
        tuple(line.split("\t", 1))
        for line in _read_data("hoi_nga_pairs.tsv").splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "\t" in line
    )
    common_capitalized = frozenset(
        line.strip().casefold()
        for line in _read_data("common_capitalized.txt").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    valid_syllables = frozenset(
        line.strip()
        for line in _read_data("syllables.txt").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    slop_list: ClassVar[list[SlopEntry]] = [
        SlopEntry(
            parts[0],
            parts[1],
            parts[2].lower() == "true",
            parts[3],
            float(parts[4]) if parts[4] else None,
            parts[5],
        )
        for line in _read_data("slop_list.txt").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        for parts in [line.split("|", 5)]
    ]
    genre_presets: ClassVar[dict[str, dict]] = {
        item.get("id", item.get("key")): item
        for item in json.loads(
            files("writestory_ai.languages.vi").joinpath("genres.json").read_text(encoding="utf-8")
        )
    }

    def normalize(self, text: str) -> str:
        return normalize_text(text)

    def count_length(self, text: str) -> int:
        return count_syllables(text)

    def search_fold(self, text: str) -> str:
        return search_fold(text)


from writestory_ai.languages.vi.checks import (  # noqa: E402
    check_accent_mix,
    check_address,
    check_dialogue,
    check_lexicon,
    check_name_variants,
    check_slop,
    check_spelling,
)

VietnamesePack.deterministic_checks = [
    check_address,
    check_name_variants,
    check_lexicon,
    check_slop,
    check_spelling,
    check_accent_mix,
    check_dialogue,
]


__all__ = ["VietnamesePack", "count_syllables", "normalize_text", "search_fold"]
