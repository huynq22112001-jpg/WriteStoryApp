from __future__ import annotations

import unicodedata

from writestory_ai.contracts.foundation import FoundationInput, FoundationWarning


def _dict(value):
    return value.model_dump(mode="python") if hasattr(value, "model_dump") else value


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn").replace(
        "đ", "d"
    )


def check_foundation(request: FoundationInput, parts: dict[str, dict]) -> list[FoundationWarning]:
    warnings: list[FoundationWarning] = []

    def warn(code: str, path: str, message: str) -> None:
        warnings.append(FoundationWarning(code=code, path=path, message=message))

    frame = _dict(parts.get("frame_core", {}))
    volume_map = frame.get("volume_map", [])
    for index, volume in enumerate(volume_map):
        start, end = volume.get("chapter_from", 1), volume.get("chapter_to", 1)
        if start > end or end > request.target_chapters:
            warn(
                "volume_range",
                f"frame_core.volume_map[{index}]",
                "Khoảng chương ngoài phạm vi tác phẩm.",
            )
    for chapter in range(1, request.target_chapters + 1) if volume_map else ():
        owners = [
            volume
            for volume in volume_map
            if volume.get("chapter_from", 2) <= chapter <= volume.get("chapter_to", 0)
        ]
        if len(owners) != 1:
            warn("volume_coverage", f"chapter:{chapter}", "Chương phải thuộc đúng một quyển.")

    cast = _dict(parts.get("cast", {}))
    characters = cast.get("characters", [])
    names: dict[str, str] = {}
    character_ids = {str(character.get("temp_id", "")) for character in characters}
    for i, character in enumerate(characters):
        character_id = str(character.get("temp_id", i))
        variants = [character.get("name", "")]
        variants.extend(alias.get("text", "") for alias in character.get("aliases", []))
        for variant in variants:
            folded = _fold(str(variant).strip())
            if not folded:
                continue
            prior = names.get(folded)
            if prior is not None and prior != character_id:
                warn(
                    "duplicate_name",
                    f"cast.characters[{i}]",
                    f"Tên/bí danh trùng sau chuẩn hóa: {variant}",
                )
            names[folded] = character_id

    relations = cast.get("relationships", [])
    address = _dict(parts.get("address_rules", {})).get("rules", [])
    address_pairs = {(rule.get("speaker"), rule.get("listener")) for rule in address}
    for i, relation in enumerate(relations) if "address_rules" in parts else ():
        left, right = relation.get("a"), relation.get("b")
        if left not in character_ids or right not in character_ids:
            warn(
                "dangling_relationship",
                f"cast.relationships[{i}]",
                "Quan hệ trỏ tới nhân vật không tồn tại.",
            )
            continue
        if left != right and (
            (left, right) not in address_pairs or (right, left) not in address_pairs
        ):
            warn(
                "address_missing_pair",
                f"relationships:{left}:{right}",
                "Cặp nhân vật cần quy tắc xưng hô hai chiều.",
            )

    events: list[dict] = []
    for key, value in parts.items():
        if key.startswith("events_"):
            events.extend(_dict(value).get("events", []))
    event_ids = {str(event.get("temp_id", "")) for event in events}
    graph: dict[str, list[str]] = {}
    chapter_counts: dict[int, int] = {}
    for index, event in enumerate(events):
        event_id = str(event.get("temp_id", f"event-{index}"))
        chapter = int(event.get("planned_chapter", 0))
        chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1
        if chapter < 1 or chapter > request.target_chapters:
            warn(
                "event_chapter_range",
                f"events:{event_id}",
                "Chương dự kiến ngoài phạm vi tác phẩm.",
            )
        missing = [dep for dep in event.get("depends_on", []) if dep not in event_ids]
        if missing:
            warn(
                "dangling_dependency",
                f"events:{event_id}",
                f"Không tìm thấy phụ thuộc: {', '.join(missing)}",
            )
        graph[event_id] = [dep for dep in event.get("depends_on", []) if dep in event_ids]

    visiting: set[str] = set()
    visited: set[str] = set()

    def has_cycle(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(has_cycle(child) for child in graph.get(node, [])):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(has_cycle(node) for node in graph):
        warn("event_dependency_cycle", "events", "Dàn ý có chu trình phụ thuộc.")

    if any(key.startswith("events_") for key in parts):
        for chapter in range(1, request.target_chapters + 1):
            count = chapter_counts.get(chapter, 0)
            if count == 0 or count > 3:
                warn(
                    "event_density",
                    f"chapter:{chapter}",
                    f"Chương có {count} sự kiện; mục tiêu 1-3.",
                )

    hooks = _dict(parts.get("hooks", {})).get("hooks", [])
    for index, hook in enumerate(hooks):
        if hook.get("due_by_chapter", request.target_chapters + 1) > request.target_chapters:
            warn(
                "hook_due_out_of_range",
                f"hooks[{index}].due_by_chapter",
                "Hạn hook vượt chương cuối.",
            )
        related = hook.get("related_event_temp_id")
        if related and related not in event_ids:
            warn(
                "dangling_dependency",
                f"hooks[{index}].related_event_temp_id",
                "Hook trỏ tới sự kiện không tồn tại.",
            )
    return warnings
