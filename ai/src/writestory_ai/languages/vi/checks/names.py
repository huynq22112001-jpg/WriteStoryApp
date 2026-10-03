from __future__ import annotations

import re
import unicodedata

from writestory_ai.languages.contracts import CheckContext, LanguageFinding
from writestory_ai.languages.vi import VietnamesePack

_PACK = VietnamesePack()


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn").replace("đ", "d")


def check_name_variants(ctx: CheckContext) -> list[LanguageFinding]:
    findings: list[LanguageFinding] = []
    variants: dict[str, tuple[str, str, str]] = {}
    for character in ctx.canon_characters:
        name = str(character.get("name", ""))
        aliases = [
            (name, "canon"),
            *((a.get("text", ""), a.get("kind", "alias")) for a in character.get("aliases", [])),
        ]
        for alias, alias_kind in aliases:
            if alias:
                variants[_fold(alias)] = (name, str(character.get("id", "")), str(alias_kind))
    seen_kinds: dict[str, set[str]] = {}
    combined_text = " ".join(p.text.casefold() for p in ctx.paragraphs)
    for character in ctx.canon_characters:
        character_id = str(character.get("id", ""))
        for alias in character.get("aliases", []):
            kind = alias.get("kind")
            text = str(alias.get("text", "")).casefold()
            if kind in {"han_viet", "thuan_viet"} and text and text in combined_text:
                seen_kinds.setdefault(character_id, set()).add(kind)
    mixed_allowed = {
        str(c.get("id")): bool(c.get("allow_mixed_naming", False)) for c in ctx.canon_characters
    }
    declared = {_fold(name) for name in ctx.declared_new_names}
    unknown_reported: set[str] = set()
    for p in ctx.paragraphs:
        pattern = r"\b[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){0,3}\b"
        for match in re.finditer(pattern, p.text):
            canonical = variants.get(_fold(match.group()))
            if canonical and _fold(match.group()) == _fold(canonical[0]):
                if canonical[2] == "canon" and match.group().casefold() != canonical[0].casefold():
                    findings.append(
                        LanguageFinding(
                            check_id="vi.name_variant",
                            kind="name",
                            severity="major",
                            paragraph_id=p.paragraph_id,
                            start=match.start(),
                            end=match.end(),
                            quote=match.group(),
                            message_key="vi.name_variant.accent",
                            params={"canonical": canonical[0]},
                            suggestion=canonical[0],
                        )
                    )
                if canonical[2] in {"han_viet", "thuan_viet"}:
                    seen_kinds.setdefault(canonical[1], set()).add(canonical[2])
            elif (
                not canonical
                and len(match.group().split()) > 1
                and _fold(match.group()) not in declared
                and match.group().casefold()
                not in getattr(_PACK, "common_capitalized", frozenset())
            ):
                start = match.start()
                at_sentence_start = start == 0 or p.text[max(0, start - 2) : start].strip() in {
                    ".",
                    "!",
                    "?",
                }
                normalized = _fold(match.group())
                if not at_sentence_start and normalized not in unknown_reported:
                    unknown_reported.add(normalized)
                    findings.append(
                        LanguageFinding(
                            check_id="vi.name_variant",
                            kind="name",
                            severity="blocker",
                            paragraph_id=p.paragraph_id,
                            start=start,
                            end=match.end(),
                            quote=match.group(),
                            message_key="vi.name_variant.unknown",
                            params={"name": match.group()},
                        )
                    )
    for character_id, kinds in seen_kinds.items():
        if len(kinds) > 1 and not mixed_allowed.get(character_id, False):
            findings.append(
                LanguageFinding(
                    check_id="vi.name_variant",
                    kind="name",
                    severity="major",
                    quote="",
                    message_key="vi.name_variant.mixed_alias",
                    params={"character_id": character_id},
                )
            )
    return findings
