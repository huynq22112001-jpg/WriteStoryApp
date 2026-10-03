import pytest

from writestory_ai.workflows.longform.reviewer import review


@pytest.mark.asyncio
async def test_review_merges_deterministic_and_llm_findings_without_duplicate_and_applies_d7():
    deterministic = {
        "id": "f1",
        "kind": "address",
        "paragraph_id": "p1",
        "quote": "ngươi",
        "needs_confirmation": True,
        "confidence": "medium",
    }

    async def evaluator(_findings):
        return {
            "findings": [dict(deterministic)],
            "confirmations": [{"finding_id": "f1", "confirmed": True}],
        }

    result = await review([deterministic], evaluator)
    assert len(result.findings) == 1
    assert result.findings[0]["severity"] == "blocker"


@pytest.mark.asyncio
async def test_review_dismisses_rejected_confirmation_and_keeps_unconfirmed_pending():
    rejected = {
        "id": "f1",
        "kind": "address",
        "needs_confirmation": True,
        "confidence": "medium",
    }

    async def dismiss(_findings):
        return {"confirmations": [{"finding_id": "f1", "confirmed": False}]}

    assert (await review([rejected], dismiss)).findings == []
    pending = await review([rejected])
    assert pending.findings[0]["confirmation_pending"] is True
    assert pending.findings[0]["severity"] == "major"
