import pytest

from writestory_ai.context.composer import ContextBlock, ProtectedContextOverBudget, compose_context
from writestory_ai.context.tokens import cut_tail, estimate_tokens
from writestory_ai.contracts.longform import OutlineProposal
from writestory_ai.contracts.paragraphs import (
    ParagraphOps,
    ParagraphText,
    apply_ops,
    render_paragraphs,
)
from writestory_ai.workflows.longform.outline_review import (
    apply_outline_proposal,
    should_review_outline,
)
from writestory_ai.workflows.longform.pacing import compute_pacing
from writestory_ai.workflows.longform.summaries import (
    ChapterSummary,
    StorySynopsis,
    summarize_hierarchy,
    summary_context_blocks,
)


def test_paragraph_ops_are_scoped_and_render_with_ids():
    paragraphs = [
        ParagraphText(paragraph_id="abcdefgh", text="Trước"),
        ParagraphText(paragraph_id="ijklmnop", text="Sau"),
    ]
    assert "[p:abcdefgh] Trước" in render_paragraphs(paragraphs)
    updated = apply_ops(
        paragraphs,
        ParagraphOps(ops=[{"paragraph_id": "abcdefgh", "action": "replace", "text": "Mới"}]),
    )
    assert updated[0].text == "Mới" and paragraphs[0].text == "Trước"
    with pytest.raises(ValueError):
        apply_ops(paragraphs, ParagraphOps(ops=[{"paragraph_id": "zzzzzzzz", "action": "delete"}]))


def test_composer_never_drops_protected_blocks():
    blocks = [
        ContextBlock(id="plan", layer="chapter", text="plan", token_estimate=7, protected=True),
        ContextBlock(id="old", layer="story", text="old", token_estimate=10),
    ]
    package, trace = compose_context(blocks, token_budget=8)
    assert package.included_ids == ["plan"] and package.dropped_ids == ["old"]
    assert trace.total_tokens == 7
    with pytest.raises(ProtectedContextOverBudget):
        compose_context(blocks, token_budget=6)
    compressed, _ = compose_context(
        blocks,
        token_budget=8,
        compressor=lambda block, budget: ContextBlock(
            id=block.id, layer=block.layer, text="summary", token_estimate=1
        ),
    )
    assert "summary" in compressed.text and compressed.token_estimate == 8


def test_tail_is_cut_at_paragraph_boundaries_and_estimate_has_margin():
    assert estimate_tokens("một hai", tokens_per_syllable=1) == 2
    tail = cut_tail([("p1", "một hai"), ("p2", "ba bốn")], min_tokens=3, max_tokens=4)
    assert tail.paragraph_ids == ["p1", "p2"] and "\n\n" in tail.text


def test_summaries_group_220_chapters_and_pacing_flags():
    summaries = [ChapterSummary(chapter_no=n, synopsis=f"chương {n}") for n in range(1, 221)]
    arcs = summarize_hierarchy(summaries, arc_size=10)
    assert len(arcs) == 22 and (arcs[-1].start_chapter, arcs[-1].end_chapter) == (211, 220)
    blocks = summary_context_blocks(
        StorySynopsis(text="Tóm tắt dài", through_chapter=220),
        arcs,
        summaries,
        current_arc_chapter=220,
        recent_count=5,
    )
    package, _ = compose_context(blocks, token_budget=100)
    assert len(package.included_ids) == 7
    assert compute_pacing(40, 10).warning == "crowded"


def test_outline_respects_locks_and_review_thresholds():
    assert should_review_outline(10, 10, 0)
    assert should_review_outline(3, 10, 2)
    result = apply_outline_proposal(
        OutlineProposal(
            changes=[
                {"story_event_id": "locked", "action": "drop"},
                {"story_event_id": "open", "action": "move", "to_chapter": 9},
            ]
        ),
        [
            {"id": "locked", "locked": True, "status": "planned"},
            {"id": "open", "status": "planned"},
        ],
    )
    assert result[0]["status"] == "planned" and result[1]["planned_chapter"] == 9
