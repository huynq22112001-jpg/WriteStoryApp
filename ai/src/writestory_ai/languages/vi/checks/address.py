from __future__ import annotations

import json
import re

from writestory_ai.languages.contracts import CheckContext, LanguageFinding
from writestory_ai.languages.vi import _read_data

_PRONOUNS = _read_data("pronouns.json")

_TERMS = sorted(
    (x for x in json.loads(_PRONOUNS)["terms"] if x["role"] != "third_person"),
    key=lambda x: len(x["text"]),
    reverse=True,
)
_VERBS = tuple(x.strip() for x in _read_data("speech_verbs.txt").splitlines() if x.strip())


def _valid_rule(rule: dict, speaker: str, listener: str, chapter: int) -> bool:
    return (
        rule.get("speaker_id") == speaker
        and rule.get("listener_id") == listener
        and rule.get("from_chapter", 1) <= chapter
        and (rule.get("until_chapter") is None or chapter <= rule["until_chapter"])
    )


def check_address(ctx: CheckContext) -> list[LanguageFinding]:
    """Conservative dialogue check. It reports only when a rule pair is explicitly supplied."""
    if not ctx.address_rules:
        return []
    people = {
        str(c.get("name", "")): str(c.get("id", "")) for c in ctx.canon_characters if c.get("name")
    }
    findings: list[LanguageFinding] = []
    for index, paragraph in enumerate(ctx.paragraphs):
        text = paragraph.text
        if not (text.lstrip().startswith(("-", "–", "—", '"', "“", "「"))):  # noqa: RUF001
            continue
        speaker_match = next(
            (
                name
                for name in people
                if re.search(
                    rf"\b{re.escape(name)}\b.*(?:{'|'.join(map(re.escape, _VERBS))})", text
                )
            ),
            None,
        )
        if speaker_match is None:
            # Alternating dialogue is medium confidence when exactly two characters are present.
            present = ctx.present_character_ids
            if len(present) != 2:
                findings.append(
                    LanguageFinding(
                        check_id="vi.address",
                        kind="address",
                        severity="minor",
                        paragraph_id=paragraph.paragraph_id,
                        quote=text[:200],
                        message_key="vi.address.pair_unresolved",
                        params={},
                    )
                )
                continue
            speaker_id = present[index % 2]
            speaker_confidence = "medium"
        else:
            speaker_id = people[speaker_match]
            speaker_confidence = "high"
        for rule in ctx.address_rules:
            if rule.get("speaker_id") != speaker_id or not _valid_rule(
                rule, speaker_id, str(rule.get("listener_id", "")), ctx.chapter_no
            ):
                continue
            listener_id = str(rule.get("listener_id", ""))
            listener_name = next(
                (name for name, ident in people.items() if ident == listener_id), None
            )
            listener_confidence = "medium"
            if listener_name and re.search(
                rf"(?iu)(?:^|[\"“‘—–-]\s*){re.escape(listener_name)}(?:\s*[,，:：])",  # noqa: RUF001
                text,
            ):
                listener_confidence = "high"
            high_pair = speaker_confidence == "high" and listener_confidence == "high"
            confidence = "high" if high_pair else "medium"
            allowed = {
                str(rule.get("self_term", "")).casefold(),
                str(rule.get("address_term", "")).casefold(),
            }
            for change in ctx.relationship_events:
                if (
                    change.get("op") == "address.change"
                    and change.get("speaker_id") == speaker_id
                    and change.get("listener_id") == rule.get("listener_id")
                ):
                    allowed.update(
                        {
                            str(change.get("self_term", "")).casefold(),
                            str(change.get("address_term", "")).casefold(),
                        }
                    )
            for item in _TERMS:
                term = item["text"]
                for match in re.finditer(rf"(?iu)(?<!\w){re.escape(term)}(?!\w)", text):
                    if term.casefold() in allowed:
                        continue
                    findings.append(
                        LanguageFinding(
                            check_id="vi.address",
                            kind="address",
                            severity="blocker" if high_pair else "major",
                            confidence=confidence,
                            paragraph_id=paragraph.paragraph_id,
                            start=match.start(),
                            end=match.end(),
                            quote=match.group(),
                            message_key="vi.address.rule_mismatch",
                            params={
                                "chapter_no": ctx.chapter_no,
                                "allowed_terms": sorted(allowed),
                                "observed_term": term,
                            },
                            suggestion=str(rule.get("address_term", "")) or None,
                            needs_confirmation=confidence == "medium",
                        )
                    )
                    break
                else:
                    continue
                break
    return findings
