from __future__ import annotations

import json

from pydantic import Field

from writestory_ai.context.composer import ContextBlock
from writestory_ai.contracts.state import StrictModel


class ChapterSummary(StrictModel):
    chapter_no: int
    synopsis: str
    events: list[str] = Field(default_factory=list)
    character_changes: list[str] = Field(default_factory=list)
    open_hooks: list[str] = Field(default_factory=list)
    token_estimate: int = 0


class ArcSummary(StrictModel):
    start_chapter: int
    end_chapter: int
    synopsis: str
    key_changes: list[str] = Field(default_factory=list)


class StorySynopsis(StrictModel):
    text: str
    through_chapter: int


def summarize_chapter(
    chapter_no: int, paragraphs: list[str], *, max_characters: int = 1200
) -> ChapterSummary:
    # Deterministic fallback; model-backed summarization is an orchestration concern.
    text = " ".join(p.strip() for p in paragraphs if p.strip())
    synopsis = text[:max_characters]
    return ChapterSummary(
        chapter_no=chapter_no, synopsis=synopsis, token_estimate=len(synopsis.split())
    )


def summarize_hierarchy(summaries: list[ChapterSummary], *, arc_size: int = 10) -> list[ArcSummary]:
    if arc_size < 1:
        raise ValueError("arc_size must be positive")
    arcs = []
    for start in range(0, len(summaries), arc_size):
        batch = summaries[start : start + arc_size]
        if batch:
            arcs.append(
                ArcSummary(
                    start_chapter=batch[0].chapter_no,
                    end_chapter=batch[-1].chapter_no,
                    synopsis=" ".join(x.synopsis for x in batch),
                    key_changes=[event for x in batch for event in x.events],
                )
            )
    return arcs


def summary_context_blocks(
    synopsis: StorySynopsis,
    arcs: list[ArcSummary],
    summaries: list[ChapterSummary],
    *,
    current_arc_chapter: int,
    recent_count: int = 5,
) -> list[ContextBlock]:
    current_arc = next(
        (a for a in arcs if a.start_chapter <= current_arc_chapter <= a.end_chapter), None
    )
    recent = [s for s in summaries if s.chapter_no <= current_arc_chapter][-max(0, recent_count) :]
    blocks = [
        ContextBlock(
            id="story.synopsis",
            layer="story",
            text=synopsis.text,
            token_estimate=max(1, len(synopsis.text.split())),
            compressible=True,
        )
    ]
    if current_arc:
        blocks.append(
            ContextBlock(
                id="story.current_arc",
                layer="story",
                text=current_arc.synopsis,
                token_estimate=max(1, len(current_arc.synopsis.split())),
                compressible=True,
            )
        )
    blocks.extend(
        ContextBlock(
            id=f"chapter.summary.{s.chapter_no}",
            layer="chapter",
            text=s.synopsis,
            token_estimate=max(1, s.token_estimate),
            compressible=True,
        )
        for s in recent
    )
    return blocks


async def summarize_chapter_with_provider(
    provider, *, model: str, chapter_no: int, chapter_text: str, prompts, max_tokens: int = 1200
) -> ChapterSummary:
    from writestory_ai.contracts.errors import StructuredOutputInvalidError
    from writestory_ai.contracts.generation import GenerationRequest, Message
    from writestory_ai.providers.collect import collect

    prompt = prompts.render(
        "longform.summary_chapter", chapter_no=chapter_no, chapter_text=chapter_text
    )
    result = await collect(
        provider,
        GenerationRequest(
            model=model, max_tokens=max_tokens, messages=[Message(role="user", content=prompt)]
        ),
    )
    try:
        return ChapterSummary.model_validate(json.loads(result.text))
    except (ValueError, TypeError) as error:
        raise StructuredOutputInvalidError("Chapter summary JSON is invalid") from error


async def summarize_arc_with_provider(
    provider, *, model: str, summaries: list[ChapterSummary], prompts, max_tokens: int = 1600
) -> ArcSummary:
    from writestory_ai.contracts.errors import StructuredOutputInvalidError
    from writestory_ai.contracts.generation import GenerationRequest, Message
    from writestory_ai.providers.collect import collect

    if not summaries:
        raise ValueError("At least one chapter summary is required")
    prompt = prompts.render(
        "longform.summary_arc",
        start_chapter=summaries[0].chapter_no,
        end_chapter=summaries[-1].chapter_no,
        summaries=[s.model_dump() for s in summaries],
    )
    result = await collect(
        provider,
        GenerationRequest(
            model=model, max_tokens=max_tokens, messages=[Message(role="user", content=prompt)]
        ),
    )
    try:
        return ArcSummary.model_validate(json.loads(result.text))
    except (ValueError, TypeError) as error:
        raise StructuredOutputInvalidError("Arc summary JSON is invalid") from error
