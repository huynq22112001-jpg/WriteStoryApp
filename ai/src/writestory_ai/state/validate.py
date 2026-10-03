from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from writestory_ai.contracts.state import StateDelta, StoryState
from writestory_ai.state.apply import state_hash


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    severity: str = "error"


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]


def validate_delta(
    state: StoryState,
    delta: StateDelta,
    paragraphs: dict[str, str] | None = None,
) -> ValidationResult:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    def error(code: str, message: str) -> None:
        errors.append(ValidationIssue(code=code, message=message))

    if delta.work_id != state.work_id or delta.base_state_chapter != state.chapter_no:
        error("V02", "base_state_chapter không khớp state hiện tại")
    if delta.base_state_hash != state_hash(state):
        error("V02", "base_state_hash không khớp state hiện tại")

    character_ids = {x.id for x in state.characters}
    location_ids = {x.id for x in state.locations}
    hook_by_id = {x.id: x for x in state.hooks}
    event_by_id = {x.story_event_id: x for x in state.events}
    fact_by_id = {x.id: x for x in state.facts}
    fact_secret_by_id = {x.id: x.is_secret for x in state.facts}
    current_time_ordinal = state.story_time.ordinal
    character_status = {x.id: x.status for x in state.characters}
    learned_facts = {x.id: set(x.knowledge) for x in state.characters}
    declared_at: dict[str, int] = {}
    changed_relationships: set[tuple[str, str]] = set()
    closed_facts: set[str] = set()
    for index, op in enumerate(delta.ops):
        if op.op == "character.add":
            new_character_id = op.character.id
            if new_character_id in character_ids:
                error("V03", f"ID nhân vật đã tồn tại: {new_character_id}")
            declared_at[new_character_id] = index
        elif op.op == "location.add":
            location_id = op.location.id
            if location_id in location_ids:
                error("V03", f"ID địa điểm đã tồn tại: {location_id}")
            declared_at[location_id] = index
        elif op.op == "fact.add":
            fact_id = op.fact.id
            declared_at[fact_id] = index
            fact_secret_by_id[fact_id] = op.fact.is_secret
        elif op.op == "hook.open":
            hook_id = op.hook.id
            declared_at[hook_id] = index
        elif op.op == "relationship.set":
            changed_relationships.add((op.a, op.b))

    def exists_before(value: str, existing: set[str], index: int) -> bool:
        return value in existing or declared_at.get(value, index) < index

    for index, op in enumerate(delta.ops):
        if op.op in {"character.update", "character.move", "character.learn"} and not exists_before(
            op.character_id, character_ids, index
        ):
            error("V03", f"Không tìm thấy nhân vật {op.character_id}")
        if op.op == "character.move" and not exists_before(op.to_location_id, location_ids, index):
            error("V12", f"Không tìm thấy địa điểm {op.to_location_id}")
        if op.op == "character.learn" and not exists_before(
            op.fact_id, set(fact_by_id), index
        ):
            error("V03", f"Không tìm thấy fact {op.fact_id}")
        if (
            op.op == "character.add"
            and op.location_id
            and not exists_before(op.location_id, location_ids, index)
        ):
            error("V03", f"Không tìm thấy địa điểm {op.location_id}")
        if op.op == "relationship.set":
            if not exists_before(op.a, character_ids, index) or not exists_before(
                op.b, character_ids, index
            ):
                error("V03", "relationship.set tham chiếu nhân vật không tồn tại")
        if op.op == "address.change":
            if not exists_before(op.speaker_id, character_ids, index) or not exists_before(
                op.listener_id, character_ids, index
            ):
                error("V03", "address.change tham chiếu nhân vật không tồn tại")
        if op.op in {"hook.advance", "hook.resolve", "hook.defer"}:
            hook = hook_by_id.get(op.hook_id)
            if hook is None and not exists_before(op.hook_id, set(hook_by_id), index):
                error("V03", f"Không tìm thấy hook {op.hook_id}")
            elif hook and hook.status in {"resolved", "superseded"}:
                error("V06", f"Hook {op.hook_id} đã đóng")
            if any(
                earlier.op in {"hook.resolve"}
                and earlier.hook_id == op.hook_id
                for earlier in delta.ops[:index]
            ):
                error("V06", f"Hook {op.hook_id} đã đóng trong delta này")
            if op.op == "hook.defer" and op.new_due_by <= delta.chapter_no:
                error("V06", "Hook defer phải có hạn sau chương hiện tại")
            if (
                op.op == "hook.defer"
                and hook
                and hook.due_by is not None
                and op.new_due_by <= hook.due_by
            ):
                error("V06", "Hook defer phải dời hạn về sau")
        if op.op in {"event.done", "event.move", "event.drop"}:
            event = event_by_id.get(op.story_event_id)
            if event is None:
                error("V03", f"Không tìm thấy event {op.story_event_id}")
            elif op.op == "event.drop" and event.status == "done":
                error("V10", f"Event {op.story_event_id} đã hoàn thành")
            elif op.op == "event.done" and (
                event.status == "done"
                or any(
                    earlier.op == "event.done"
                    and earlier.story_event_id == op.story_event_id
                    for earlier in delta.ops[:index]
                )
            ):
                error("V10", f"Event {op.story_event_id} đã hoàn thành")
            elif op.op == "event.done" and event:
                unfinished = [
                    dep
                    for dep in event.depends_on
                    if not any(
                        candidate.story_event_id == dep and candidate.status == "done"
                        for candidate in state.events
                    )
                    and not any(
                        earlier.op == "event.done" and earlier.story_event_id == dep
                        for earlier in delta.ops[:index]
                    )
                ]
                if unfinished:
                    error("V10", f"Event phụ thuộc chưa hoàn thành: {', '.join(unfinished)}")
            if op.op == "event.move" and op.to_chapter <= delta.chapter_no:
                error("V10", "Event không được chuyển về chương hiện tại hoặc quá khứ")
        if (
            op.op == "address.change"
            and (op.speaker_id, op.listener_id) not in changed_relationships
        ):
            error("V11", "address.change cần relationship.set cùng cặp")
        if (
            op.op == "time.advance"
            and not op.flashback
            and not op.in_flashback
            and op.to.ordinal < current_time_ordinal
        ):
            error("V05", "Story time không được lùi nếu không phải hồi tưởng")
        if op.op == "time.advance" and not op.flashback and not op.in_flashback:
            current_time_ordinal = op.to.ordinal
        if op.op == "relationship.set" and (op.a == op.b or not -3 <= op.intensity <= 3):
            error("V15", "Quan hệ không hợp lệ")
        if delta.source == "pipeline" and op.op not in {"hook.defer", "event.move", "event.drop"}:
            if op.evidence is None:
                error("V08", f"{op.op} thiếu evidence")
        if op.evidence and op.evidence.kind == "paragraph":
            if op.evidence.chapter_no != delta.chapter_no:
                error("V08", "Evidence không thuộc chương đang xét")
            original = paragraphs.get(op.evidence.paragraph_id) if paragraphs is not None else None
            if original is None:
                error("V08", "Evidence không trỏ tới đoạn của candidate")
            else:
                from writestory_ai.languages.vi.normalizer import normalize_text

                if normalize_text(op.evidence.quote) not in normalize_text(original):
                    error("V08", "Evidence quote không khớp candidate")
        if op.op == "fact.close":
            fact = next((f for f in state.facts if f.id == op.fact_id), None)
            if fact is None and not exists_before(op.fact_id, {f.id for f in state.facts}, index):
                error("V03", f"Không tìm thấy fact {op.fact_id}")
            elif (fact is not None and fact.valid_until is not None) or op.fact_id in closed_facts:
                error("V09", f"Fact {op.fact_id} đã đóng")
            closed_facts.add(op.fact_id)
        if op.op == "fact.add":
            candidate = op.fact
            duplicate_in_state = any(
                f.valid_until is None
                and (f.subject.casefold(), f.predicate.casefold(), f.object.casefold())
                == (
                    candidate.subject.casefold(),
                    candidate.predicate.casefold(),
                    candidate.object.casefold(),
                )
                for f in state.facts
            )
            duplicate_in_delta = any(
                earlier.op == "fact.add"
                and (
                    earlier.fact.subject.casefold(),
                    earlier.fact.predicate.casefold(),
                    earlier.fact.object.casefold(),
                )
                == (
                    candidate.subject.casefold(),
                    candidate.predicate.casefold(),
                    candidate.object.casefold(),
                )
                for earlier in delta.ops[:index]
            )
            if duplicate_in_state or duplicate_in_delta:
                warnings.append(
                    ValidationIssue(
                        code="V09", message="Fact đang hiệu lực bị lặp", severity="warning"
                    )
                )
        if op.op == "character.update":
            status = character_status.get(op.character_id)
            if status in {"dead", "missing"} and not op.in_flashback:
                if status == "dead" and op.status == "alive" and op.override_reason:
                    warnings.append(
                        ValidationIssue(
                            code="V04", message="Nhân vật được hồi sinh", severity="major"
                        )
                    )
                else:
                    error("V04", f"Không thể cập nhật nhân vật {status}")
            if op.status is not None:
                character_status[op.character_id] = op.status
        if op.op == "character.move":
            status = character_status.get(op.character_id)
            if status in {"dead", "missing"} and not op.in_flashback:
                error("V04", f"Không thể di chuyển nhân vật {status}")
        if op.op == "character.learn":
            status = character_status.get(op.character_id)
            if status in {"dead", "missing"} and not op.in_flashback:
                error("V04", f"Không thể cập nhật nhân vật {status}")
            learned_facts.setdefault(op.character_id, set()).add(op.fact_id)
        if op.op == "character.add":
            character_id = str(op.character.id)
            character_status[character_id] = "alive"
            learned_facts[character_id] = set()

    if delta.ending_state:
        alive_after = {c.id for c in state.characters if c.status == "alive"}
        locations_after = {c.id: c.location_id for c in state.characters}
        for op in delta.ops:
            if op.op == "character.add":
                character_id = op.character.id
                alive_after.add(character_id)
                locations_after[character_id] = op.location_id
            elif op.op == "character.update" and op.status and not op.in_flashback:
                if op.status == "alive":
                    alive_after.add(op.character_id)
                else:
                    alive_after.discard(op.character_id)
            elif op.op == "character.move" and not op.in_flashback:
                locations_after[op.character_id] = op.to_location_id
        for present in delta.ending_state.present:
            if present.character_id not in alive_after:
                error("V13", f"Nhân vật cuối chương không sống: {present.character_id}")
            if (
                delta.ending_state.location_id
                and locations_after.get(present.character_id) != delta.ending_state.location_id
            ):
                warnings.append(
                    ValidationIssue(
                        code="V13",
                        message=f"Vị trí chưa khớp: {present.character_id}",
                        severity="warning",
                    )
                )
        advances = [
            op.to
            for op in delta.ops
            if op.op == "time.advance" and not op.flashback and not op.in_flashback
        ]
        expected_time = advances[-1] if advances else state.story_time
        if delta.ending_state.story_time != expected_time:
            error("V13", "ending_state.story_time không khớp state sau delta")
    for use in delta.knowledge_uses:
        character = next((c for c in state.characters if c.id == use.character_id), None)
        evidence = use.evidence
        if not exists_before(use.character_id, character_ids, len(delta.ops)):
            error("V03", f"Không tìm thấy nhân vật {use.character_id}")
        if not exists_before(use.fact_id, set(fact_by_id), len(delta.ops)):
            error("V03", f"Không tìm thấy fact {use.fact_id}")
        candidate_text = paragraphs.get(evidence.paragraph_id) if paragraphs is not None else None
        if evidence.chapter_no != delta.chapter_no or candidate_text is None:
            error("V08", "KnowledgeUse evidence không khớp candidate")
        else:
            from writestory_ai.languages.vi.normalizer import normalize_text

            if normalize_text(evidence.quote) not in normalize_text(candidate_text):
                error("V08", "KnowledgeUse evidence không khớp candidate")
        if (
            fact_secret_by_id.get(use.fact_id, False)
            and use.fact_id not in (character.knowledge if character else [])
            and use.fact_id not in learned_facts.get(use.character_id, set())
        ):
            error("V07", f"Nhân vật chưa biết bí mật {use.fact_id}")
    for hook in state.hooks:
        deferred = any(op.op == "hook.defer" and op.hook_id == hook.id for op in delta.ops)
        resolved = any(op.op == "hook.resolve" and op.hook_id == hook.id for op in delta.ops)
        if (
            hook.due_by is not None
            and hook.due_by < delta.chapter_no
            and hook.status not in {"resolved", "superseded"}
            and not deferred
            and not resolved
        ):
            warnings.append(
                ValidationIssue(code="V14", message=f"Hook quá hạn: {hook.id}", severity="major")
            )
    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)
