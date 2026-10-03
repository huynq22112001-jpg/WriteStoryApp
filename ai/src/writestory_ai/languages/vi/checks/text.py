from __future__ import annotations

import re

from writestory_ai.languages.contracts import CheckContext, LanguageFinding
from writestory_ai.languages.vi import VietnamesePack

_PACK = VietnamesePack()


def _decode_telex(token: str) -> str:
    value = token.casefold()
    tone = {"s": "acute", "f": "grave", "r": "hook", "x": "tilde", "j": "dot"}
    mark = tone.get(value[-1:])
    if mark:
        value = value[:-1]
    for source, target in (
        ("dd", "đ"),
        ("aa", "â"),
        ("aw", "ă"),
        ("ee", "ê"),
        ("oo", "ô"),
        ("ow", "ơ"),
        ("uw", "ư"),
    ):
        value = value.replace(source, target)
    return _apply_tone(value, mark)


def _decode_vni(token: str) -> str:
    value = token.casefold()
    tone_digit = value[-1:] if value[-1:] in "12345" else None
    if tone_digit:
        value = value[:-1]
    for source, target in (
        ("a6", "â"),
        ("a8", "ă"),
        ("e6", "ê"),
        ("o6", "ô"),
        ("o7", "ơ"),
        ("u7", "ư"),
        ("d9", "đ"),
    ):
        value = value.replace(source, target)
    tone = {"1": "acute", "2": "grave", "3": "hook", "4": "tilde", "5": "dot"}.get(tone_digit)
    return _apply_tone(value, tone)


def _apply_tone(value: str, tone: str | None) -> str:
    if tone is None:
        return value
    import unicodedata

    marks = {
        "acute": "\u0301",
        "grave": "\u0300",
        "hook": "\u0309",
        "tilde": "\u0303",
        "dot": "\u0323",
    }
    vowels = "aăâeêioôơuưy"
    positions = [i for i, char in enumerate(value) if char in vowels]
    if not positions:
        return value
    # Vietnamese typing convention puts the tone on the last vowel unless a glide follows.
    index = positions[-1]
    if len(positions) >= 2 and value[positions[-1]] in "iuy" and positions[-1] == len(value) - 1:
        index = positions[-2]
    chars = list(value)
    chars[index] = unicodedata.normalize("NFC", chars[index] + marks[tone])
    return "".join(chars)


def _has_impossible_final(token: str) -> bool:
    import unicodedata

    folded = "".join(
        char for char in unicodedata.normalize("NFD", token) if unicodedata.category(char) != "Mn"
    )
    vowels = "aăâeêioôơuưy"
    if not folded or folded[-1] in vowels:
        return False
    return not any(folded.endswith(coda) for coda in ("ch", "ng", "nh", "c", "m", "n", "p", "t"))


def check_slop(ctx: CheckContext) -> list[LanguageFinding]:
    findings = []
    entries = list(_PACK.slop_list) + list(ctx.profile.get("slop", []))
    thresholds = ctx.profile.get("slop_density_threshold", {})
    for entry in entries:
        get = (
            entry.get
            if isinstance(entry, dict)
            else lambda key, default=None, value=entry: getattr(value, key, default)
        )
        entry_id = str(get("id", "custom"))
        entry_pattern = str(get("pattern", ""))
        pattern = entry_pattern if get("is_regex", False) else re.escape(entry_pattern)
        paragraph_start = get("scope", "anywhere") == "paragraph_start"
        if paragraph_start:
            pattern = r"^\s*(?:[-–—]\s*)?" + pattern  # noqa: RUF001
        matches = [
            (paragraph, match)
            for paragraph in ctx.paragraphs
            for match in re.finditer(pattern, paragraph.text, re.IGNORECASE)
        ]
        max_per_1000 = get("max_per_1000_units")
        if isinstance(thresholds, (int, float)):
            max_per_1000 = float(thresholds)
        elif isinstance(thresholds, dict):
            max_per_1000 = thresholds.get(entry_id, thresholds.get(entry_pattern, max_per_1000))
        if max_per_1000 is not None:
            units = max(1, sum(_PACK.count_length(p.text) for p in ctx.paragraphs))
            if len(matches) / units * 1000 <= float(max_per_1000):
                continue
            examples = [p.paragraph_id for p, _ in matches[:5]]
            findings.append(
                LanguageFinding(
                    check_id="vi.slop",
                    kind="slop",
                    severity="minor",
                    paragraph_id=examples[0] if examples else None,
                    quote=matches[0][1].group()[:200] if matches else "",
                    message_key="vi.slop.density",
                    params={"entry_id": entry_id, "count": len(matches), "paragraph_ids": examples},
                )
            )
            continue
        for paragraph, match in matches:
            findings.append(
                LanguageFinding(
                    check_id="vi.slop",
                    kind="slop",
                    severity="minor",
                    paragraph_id=paragraph.paragraph_id,
                    start=match.start(),
                    end=match.end(),
                    quote=match.group()[:200],
                    message_key="vi.slop.phrase",
                    params={"entry_id": entry_id},
                )
            )
    return findings


def check_spelling(ctx: CheckContext) -> list[LanguageFinding]:
    findings = []
    valid_syllables = {s.casefold() for s in _PACK.valid_syllables}
    allowed = {
        str(x).casefold() for x in ctx.profile.get("spelling_allowlist", [])
    } | _PACK.foreign_allowlist
    for character in ctx.canon_characters:
        names = [character.get("name", "")]
        names.extend(alias.get("text", "") for alias in character.get("aliases", []))
        for name in names:
            allowed.update(
                str(part).casefold() for part in re.findall(r"(?u)\b[^\W\d_]+\b", str(name))
            )
    for p in ctx.paragraphs:
        for match in re.finditer(r"(?u)\b[^\W_]+\b", p.text):
            token = match.group().casefold()
            if token.isdigit():
                continue
            if token in allowed or token in valid_syllables:
                continue
            # Capitalized unknown words are likely names; F08 name checks handle those.
            if match.group()[:1].isupper():
                continue
            decoded = _decode_telex(token) if re.search(r"(?:[sfrxj]|dd)", token) else ""
            encoding = "telex"
            if decoded not in _PACK.valid_syllables:
                decoded = _decode_vni(token) if re.search(r"[0-9]", token) else ""
                encoding = "vni"
            if decoded:
                findings.append(
                    LanguageFinding(
                        check_id="vi.spelling",
                        kind="spelling",
                        severity="minor",
                        paragraph_id=p.paragraph_id,
                        start=match.start(),
                        end=match.end(),
                        quote=match.group(),
                        message_key="vi.spelling.telex_suspected",
                        params={"encoding": encoding},
                        needs_confirmation=False,
                        suggestion=decoded,
                    )
                )
                continue
            # The seed lexicon is intentionally incomplete. Flag only visibly Vietnamese
            # forms absent from it; plain ASCII foreign words stay outside this check.
            if any(ord(char) > 127 for char in token) and _has_impossible_final(token):
                findings.append(
                    LanguageFinding(
                        check_id="vi.spelling",
                        kind="spelling",
                        severity="minor",
                        paragraph_id=p.paragraph_id,
                        start=match.start(),
                        end=match.end(),
                        quote=match.group(),
                        message_key="vi.spelling.invalid_syllable",
                        params={"limit": "seed_dictionary"},
                    )
                )
    return findings


def check_accent_mix(ctx: CheckContext) -> list[LanguageFinding]:
    style = str(ctx.profile.get("tone_mark_style", "new"))
    mismatches = {
        "new": ("hoà", "khoẻ", "thuỷ", "thuý", "xoè", "loà", "nguỵ"),
        "old": ("hòa", "khỏe", "thủy", "thúy", "xòe", "lòa", "ngụy"),
    }.get(style, ())
    matches = []
    for p in ctx.paragraphs:
        for token in mismatches:
            pattern = rf"(?iu)(?<!\w){re.escape(token)}(?!\w)"
            matches.extend((p, match) for match in re.finditer(pattern, p.text))
    if not matches:
        return []
    return [
        LanguageFinding(
            check_id="vi.accent_mix",
            kind="tone_mark_style",
            severity="major",
            paragraph_id=matches[0][0].paragraph_id,
            start=matches[0][1].start(),
            end=matches[0][1].end(),
            quote=matches[0][1].group(),
            message_key="vi.accent_mix.mixed_style",
            params={
                "expected_style": style,
                "count": len(matches),
                "paragraph_ids": list(dict.fromkeys(p.paragraph_id for p, _ in matches))[:5],
            },
        )
    ]


def check_dialogue(ctx: CheckContext) -> list[LanguageFinding]:
    style = str(ctx.profile.get("dialogue_style", "dash"))
    findings = []
    for p in ctx.paragraphs:
        trimmed = p.text.lstrip()
        bad = (style == "dash" and trimmed.startswith(('"', "“", "「"))) or (
            style == "quotes" and trimmed.startswith(("-", "–", "—"))  # noqa: RUF001
        )
        bad = (
            bad
            or p.text.count("“") != p.text.count("”")
            or p.text.count("「") != p.text.count("」")
        )
        bad = bad or p.text.count('"') % 2 == 1
        bad = bad or ("–" in p.text and "—" in p.text)  # noqa: RUF001
        if bad:
            findings.append(
                LanguageFinding(
                    check_id="vi.dialogue",
                    kind="dialogue",
                    severity="minor",
                    paragraph_id=p.paragraph_id,
                    quote=p.text[:200],
                    message_key="vi.dialogue.style_mismatch",
                )
            )
        for match in re.finditer(r"(?<=\w)\s+([,.;:!?])", p.text):
            findings.append(
                LanguageFinding(
                    check_id="vi.dialogue",
                    kind="punctuation",
                    severity="minor",
                    paragraph_id=p.paragraph_id,
                    start=match.start(),
                    end=match.end(),
                    quote=match.group(),
                    message_key="vi.punctuation.space_before",
                )
            )
    return findings


def check_lexicon(ctx: CheckContext) -> list[LanguageFinding]:
    era = ctx.genre_preset.get("era")
    if era != "co_trang":
        return []
    # Story-specific allowlists and transmigrator exemptions are honored.
    allow = {str(x).casefold() for x in ctx.profile.get("anachronism_allow", [])}
    terms = _PACK.anachronisms
    findings = []
    transmigrators = {str(c.get("id")) for c in ctx.canon_characters if c.get("is_transmigrator")}
    for p in ctx.paragraphs:
        if ctx.present_character_ids and set(ctx.present_character_ids) <= transmigrators:
            continue
        for term in terms:
            match = re.search(re.escape(term), p.text, re.IGNORECASE)
            if match and term.casefold() not in allow:
                findings.append(
                    LanguageFinding(
                        check_id="vi.lexicon",
                        kind="anachronism",
                        severity="minor",
                        paragraph_id=p.paragraph_id,
                        start=match.start(),
                        end=match.end(),
                        quote=match.group(),
                        message_key="vi.lexicon.anachronism",
                        params={"term": term},
                    )
                )
        if ctx.profile.get("vocab_register") == "thuan_viet":
            text = p.text.casefold()
            found = [
                term for term in _PACK.han_viet_terms for _ in re.finditer(re.escape(term), text)
            ]
            limit = ctx.profile.get(
                "han_viet_max_per_1000", ctx.genre_preset.get("han_viet_max_per_1000")
            )
            units = max(1, len(text.split()))
            if found and limit is not None and len(found) / units * 1000 > limit:
                findings.append(
                    LanguageFinding(
                        check_id="vi.lexicon",
                        kind="lexicon",
                        severity="minor",
                        paragraph_id=p.paragraph_id,
                        quote=p.text[:200],
                        message_key="vi.lexicon.han_viet_density",
                        params={"terms": found[:5], "count": len(found)},
                    )
                )
    return findings
