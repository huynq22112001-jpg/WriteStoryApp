from __future__ import annotations

import hashlib
import json

from writestory_ai.contracts.state import StateDelta, StoryState


def state_hash(state: StoryState) -> str:
    payload = state.model_dump(mode="json")
    for name, key in (
        ("characters", "id"),
        ("relationships", "a"),
        ("facts", "id"),
        ("hooks", "id"),
        ("events", "story_event_id"),
        ("locations", "id"),
    ):
        payload[name] = sorted(
            payload[name], key=lambda item: tuple(str(item.get(k, "")) for k in (key, "b"))
        )
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def apply_delta(state: StoryState, delta: StateDelta) -> tuple[StoryState, str]:
    """Apply state operations without I/O; return a new state and its canonical hash."""
    if state.work_id != delta.work_id or state.chapter_no != delta.base_state_chapter:
        raise ValueError("StateDelta base does not match StoryState")
    if delta.base_state_hash != state_hash(state):
        raise ValueError("StateDelta base hash does not match StoryState")
    updated = state.model_copy(deep=True)
    temporary_ids: dict[str, str] = {}

    def resolve(value: str) -> str:
        return temporary_ids.get(value, value)

    for op in delta.ops:
        data = op.model_dump(mode="python", exclude_none=True)
        kind = data.pop("op")
        data.pop("evidence", None)
        data.pop("reason", None)
        flashback = data.pop("in_flashback", False)
        if kind == "character.add":
            character = dict(data["character"])
            old_id = str(character["id"])
            character["id"] = (
                f"character:{len(updated.characters) + 1}" if old_id.startswith("new:") else old_id
            )
            temporary_ids[old_id] = character["id"]
            character = {
                "id": character["id"],
                "status": "alive",
                "location_id": resolve(data["location_id"]) if data.get("location_id") else None,
                "condition": "",
                "goals": [],
                "knowledge": [],
                "inventory": [],
            }
            from writestory_ai.contracts.state import CharacterState

            updated.characters.append(CharacterState.model_validate(character))
        elif kind == "character.update":
            item = next(x for x in updated.characters if x.id == resolve(data["character_id"]))
            if not flashback:
                for attr in ("status", "condition"):
                    if attr in data:
                        setattr(item, attr, data[attr])
                if data.get("goals_set") is not None:
                    item.goals = data["goals_set"]
                item.goals = [x for x in item.goals if x not in data.get("goals_remove", [])]
                item.goals.extend(x for x in data.get("goals_add", []) if x not in item.goals)
                item.inventory = [
                    x for x in item.inventory if x not in data.get("inventory_remove", [])
                ]
                item.inventory.extend(
                    x for x in data.get("inventory_add", []) if x not in item.inventory
                )
        elif kind == "character.move":
            if not flashback:
                next(
                    x for x in updated.characters if x.id == resolve(data["character_id"])
                ).location_id = resolve(data["to_location_id"])
        elif kind == "character.learn":
            item = next(x for x in updated.characters if x.id == resolve(data["character_id"]))
            fact = resolve(data["fact_id"])
            if fact not in item.knowledge:
                item.knowledge.append(fact)
        elif kind == "relationship.set":
            from writestory_ai.contracts.state import Relationship

            rel = Relationship(**data, since_chapter=delta.chapter_no)
            updated.relationships = [
                r for r in updated.relationships if (r.a, r.b) != (rel.a, rel.b)
            ] + [rel]
        elif kind == "fact.add":
            from writestory_ai.contracts.state import FactState

            fact = dict(data["fact"])
            old_id = str(fact["id"])
            fact["id"] = f"fact:{len(updated.facts) + 1}" if old_id.startswith("new:") else old_id
            temporary_ids[old_id] = fact["id"]
            fact["valid_from"] = delta.chapter_no
            updated.facts.append(FactState.model_validate(fact))
        elif kind == "fact.close":
            next(
                x for x in updated.facts if x.id == resolve(data["fact_id"])
            ).valid_until = delta.chapter_no
        elif kind == "hook.open":
            from writestory_ai.contracts.state import HookState

            hook = dict(data["hook"])
            old_id = str(hook["id"])
            hook["id"] = f"hook:{len(updated.hooks) + 1}" if old_id.startswith("new:") else old_id
            temporary_ids[old_id] = hook["id"]
            hook["opened_at"] = delta.chapter_no
            updated.hooks.append(HookState.model_validate(hook))
        elif kind in {"hook.advance", "hook.resolve", "hook.defer"}:
            hook = next(x for x in updated.hooks if x.id == resolve(data["hook_id"]))
            if kind == "hook.advance":
                hook.status, hook.last_advanced = "progressing", delta.chapter_no
            elif kind == "hook.resolve":
                hook.status = "superseded" if data.get("as_superseded") else "resolved"
            else:
                hook.status, hook.due_by = "deferred", data["new_due_by"]
        elif kind in {"event.done", "event.move", "event.drop"}:
            event = next(
                x for x in updated.events if x.story_event_id == resolve(data["story_event_id"])
            )
            if kind == "event.done":
                event.status, event.done_chapter = "done", delta.chapter_no
            elif kind == "event.move":
                event.status, event.planned_chapter = "moved", data["to_chapter"]
            else:
                event.status = "dropped"
        elif kind == "time.advance" and not (flashback or data.get("flashback")):
            from writestory_ai.contracts.state import StoryTime

            updated.story_time = StoryTime.model_validate(data["to"])
        elif kind == "location.add":
            from writestory_ai.contracts.state import Location

            location = dict(data["location"])
            old_id = str(location["id"])
            location["id"] = (
                f"location:{len(updated.locations) + 1}" if old_id.startswith("new:") else old_id
            )
            temporary_ids[old_id] = location["id"]
            updated.locations.append(Location.model_validate(location))

    updated.chapter_no = delta.chapter_no
    if delta.ending_state:
        present = {x.character_id for x in delta.ending_state.present}
        for character in updated.characters:
            character.in_last_scene = character.id in present
            if character.in_last_scene:
                character.last_seen_chapter = delta.chapter_no
    return updated, state_hash(updated)
