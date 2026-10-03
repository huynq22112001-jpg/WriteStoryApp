from writestory_ai.languages.contracts import CheckContext
from writestory_ai.languages.vi.checks import (
    check_accent_mix,
    check_address,
    check_dialogue,
    check_lexicon,
    check_name_variants,
    check_slop,
    check_spelling,
)


def _context(text: str, **values) -> CheckContext:
    return CheckContext(
        work_id="w", chapter_no=3, paragraphs=[{"paragraph_id": "abcd1234", "text": text}], **values
    )


def test_address_ignores_story_without_explicit_rules():
    assert check_address(_context("— Ta không đồng ý!")) == []


def test_address_requires_confirmation_for_medium_pair():
    ctx = _context(
        "— Huynh đi đi!",
        present_character_ids=["a", "b"],
        address_rules=[
            {
                "speaker_id": "a",
                "listener_id": "b",
                "self_term": "ta",
                "address_term": "ngươi",
                "from_chapter": 1,
            }
        ],
        canon_characters=[],
    )
    results = check_address(ctx)
    assert results and results[0].severity == "major" and results[0].needs_confirmation


def test_address_change_allows_new_term_in_same_chapter():
    ctx = _context(
        "— Huynh đi trước đi!",
        present_character_ids=["a", "b"],
        address_rules=[
            {
                "speaker_id": "a",
                "listener_id": "b",
                "self_term": "ta",
                "address_term": "ngươi",
                "from_chapter": 1,
            }
        ],
        relationship_events=[
            {
                "op": "address.change",
                "speaker_id": "a",
                "listener_id": "b",
                "self_term": "ta",
                "address_term": "huynh",
            }
        ],
    )
    assert check_address(ctx) == []


def test_address_high_confidence_speaker_and_listener_is_blocker():
    ctx = _context(
        '— Lâm Phong nói: "Hàn Vũ, huynh hãy đi trước."',
        canon_characters=[{"id": "a", "name": "Lâm Phong"}, {"id": "b", "name": "Hàn Vũ"}],
        address_rules=[
            {
                "speaker_id": "a",
                "listener_id": "b",
                "self_term": "ta",
                "address_term": "ngươi",
                "from_chapter": 1,
            }
        ],
    )
    findings = check_address(ctx)
    assert findings and findings[0].severity == "blocker" and findings[0].confidence == "high"


def test_name_variant_flags_missing_tone_marks():
    ctx = _context(
        "Lâm Phong bước tới. Lam Phong nhìn quanh.",
        canon_characters=[{"id": "c1", "name": "Lâm Phong", "aliases": []}],
    )
    assert any(x.suggestion == "Lâm Phong" for x in check_name_variants(ctx))


def test_name_variant_flags_mixed_aliases_and_unplanned_name():
    ctx = _context(
        "anh gặp Nam Phong, sau đó gặp Lam Phong. anh hỏi về Bạch Vân.",
        canon_characters=[
            {
                "id": "c1",
                "name": "Lâm Phong",
                "aliases": [
                    {"text": "Nam Phong", "kind": "thuan_viet"},
                    {"text": "Lam Phong", "kind": "han_viet"},
                ],
            }
        ],
    )
    results = check_name_variants(ctx)
    assert any(x.message_key == "vi.name_variant.mixed_alias" for x in results)
    assert any(x.message_key == "vi.name_variant.unknown" for x in results)


def test_slop_and_dialogue_checks():
    ctx = _context("Trong khoảnh khắc ấy, anh quay lại.", profile={"dialogue_style": "dash"})
    findings = check_slop(ctx)
    assert findings and all(f.severity == "minor" for f in findings)


def test_slop_profile_can_add_phrases_and_override_density():
    text = " ".join(["không khỏi"] * 6 + ["và"] * 30)
    ctx = _context(
        text,
        profile={
            "slop_density_threshold": {"cannot.help": 1},
            "slop": [{"id": "author.phrase", "pattern": "bỗng nhiên", "scope": "anywhere"}],
        },
    )
    assert any(f.message_key == "vi.slop.density" for f in check_slop(ctx))
    assert any(
        f.params.get("entry_id") == "author.phrase"
        for f in check_slop(
            _context(
                "Bỗng nhiên anh quay lại.",
                profile={"slop": [{"id": "author.phrase", "pattern": "bỗng nhiên"}]},
            )
        )
    )


def test_spelling_and_tone_mark_checks():
    ctx = _context("sữa chữa, hoà bình.", profile={"tone_mark_style": "new"})
    spelling = check_spelling(ctx)
    assert spelling == []  # Hỏi/ngã cần từ điển bigram theo D45.
    accent = check_accent_mix(ctx)
    assert len(accent) == 1 and accent[0].params["count"] == 1


def test_telex_leftovers_are_warnings_but_hoi_nga_is_an_explicit_limit():
    ctx = _context("tieengs ddi nguwowif hoaf tiếng đi", profile={"spelling_allowlist": ["ddi"]})
    quotes = {finding.quote for finding in check_spelling(ctx)}
    assert {"tieengs", "nguwowif", "hoaf"} <= quotes
    assert "ddi" not in quotes
    assert check_spelling(_context("dể dàng, sữa chữa.")) == []


def test_telex_and_vni_are_flagged_only_when_the_decoded_syllable_is_known():
    ctx = _context("tieengs tie6ng1 tieengx tieeng", profile={})
    findings = check_spelling(ctx)
    assert {item.quote: item.suggestion for item in findings} == {
        "tieengs": "tiếng",
        "tie6ng1": "tiếng",
    }


def test_spelling_flags_unknown_vietnamese_syllable_but_leaves_ascii_foreign_word_alone():
    findings = check_spelling(_context("qắx novel", profile={}))
    assert [(f.quote, f.message_key) for f in findings] == [("qắx", "vi.spelling.invalid_syllable")]


def test_dialogue_check_flags_unbalanced_quotes():
    ctx = _context("“Một câu thoại.", profile={"dialogue_style": "quotes"})
    assert check_dialogue(ctx)


def test_lexicon_honors_story_allowlist():
    ctx = _context("Anh cầm điện thoại.", genre_preset={"era": "co_trang"})
    assert check_lexicon(ctx)
    ctx.profile["anachronism_allow"] = ["điện thoại"]
    assert not check_lexicon(ctx)
