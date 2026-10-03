from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any


def new_paragraph_id() -> str:
    return uuid.uuid4().hex[:8]


def project_doc(doc: dict[str, Any]) -> tuple[list[dict[str, Any]], str, str]:
    paragraphs: list[dict[str, Any]] = []
    texts: list[str] = []

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            return
        kind = node.get("type")
        if kind in {"paragraph", "heading", "horizontalRule"}:
            text = "* * *" if kind == "horizontalRule" else _inline_text(node.get("content", []))
            attrs = node.setdefault("attrs", {})
            paragraph_id = attrs.get("paragraph_id") or attrs.get("id")
            if not paragraph_id:
                paragraph_id = new_paragraph_id()
            while str(paragraph_id) in {item["id"] for item in paragraphs}:
                paragraph_id = new_paragraph_id()
            item = {"id": str(paragraph_id), "type": kind, "text": text}
            if kind == "heading":
                item["level"] = attrs.get("level", 1)
            paragraphs.append(item)
            texts.append(text)
            attrs["paragraph_id"] = paragraph_id
        for child in node.get("content", []):
            visit(child)

    visit(doc)
    plain = "\n\n".join(texts)
    content_hash = hashlib.sha256(
        json.dumps(paragraphs, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return paragraphs, plain, content_hash


def _inline_text(nodes: Any) -> str:
    if not isinstance(nodes, list):
        return ""
    parts = []
    for node in nodes:
        if isinstance(node, dict):
            if node.get("type") == "text" and isinstance(node.get("text"), str):
                parts.append(node["text"])
            else:
                parts.append(_inline_text(node.get("content", [])))
    return "".join(parts)


def validate_doc(doc: dict[str, Any], *, max_bytes: int = 2 * 1024 * 1024) -> None:
    if (
        not isinstance(doc, dict)
        or doc.get("type") != "doc"
        or not isinstance(doc.get("content", []), list)
    ):
        raise ValueError("invalid_document")
    if len(json.dumps(doc, ensure_ascii=False).encode("utf-8")) > max_bytes:
        raise ValueError("document_too_large")
    ids: list[str] = []
    for node in doc.get("content", []):
        if not isinstance(node, dict) or node.get("type") not in {
            "paragraph",
            "heading",
            "horizontalRule",
            "blockquote",
        }:
            raise ValueError("unsupported_node")
        if node.get("type") == "blockquote":
            nested = node.get("content", [])
            if not isinstance(nested, list) or any(
                not isinstance(child, dict) or child.get("type") != "paragraph" for child in nested
            ):
                raise ValueError("unsupported_node")
            inspect = nested
        else:
            inspect = [node]
        for block in inspect:
            attrs = block.get("attrs") or {}
            paragraph_id = attrs.get("paragraph_id") or attrs.get("id")
            if not isinstance(paragraph_id, str) or not re.fullmatch(r"[a-z0-9]{8}", paragraph_id):
                raise ValueError("invalid_paragraph_id")
            ids.append(paragraph_id)
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_paragraph_id")


def align_paragraphs(
    before: list[dict[str, Any]], after: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    from difflib import SequenceMatcher

    matcher = SequenceMatcher(
        a=[(p["id"], p.get("text", "")) for p in before],
        b=[(p["id"], p.get("text", "")) for p in after],
        autojunk=False,
    )
    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        result.append({"op": tag, "before": before[i1:i2], "after": after[j1:j2]})
    return result
