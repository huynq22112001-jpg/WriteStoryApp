import pytest

from writestory_be.modules.chapters.domain import align_paragraphs, project_doc, validate_doc


def test_project_doc_extracts_paragraphs_and_aligns_edits():
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {"paragraph_id": "a"},
                "content": [{"type": "text", "text": "Xin chào"}],
            },
            {
                "type": "paragraph",
                "attrs": {"paragraph_id": "b"},
                "content": [{"type": "text", "text": "Thế giới"}],
            },
        ],
    }
    paragraphs, plain, digest = project_doc(doc)
    assert [row["id"] for row in paragraphs] == ["a", "b"]
    assert plain == "Xin chào\n\nThế giới"
    assert len(digest) == 64
    changed = [{"id": "a", "type": "paragraph", "text": "Đã sửa"}]
    ops = align_paragraphs(paragraphs, changed)
    assert ops[0]["op"] == "replace"


def test_project_doc_generates_stable_paragraph_identifier_in_document():
    doc = {"type": "doc", "content": [{"type": "paragraph"}]}
    paragraphs, _, _ = project_doc(doc)
    assert len(paragraphs[0]["id"]) == 8
    assert doc["content"][0]["attrs"]["paragraph_id"] == paragraphs[0]["id"]


def test_projection_includes_headings_and_scene_breaks_and_hash_ignores_marks():
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"paragraph_id": "heading1"},
                "content": [{"type": "text", "text": "Tên"}],
            },
            {"type": "horizontalRule", "attrs": {"paragraph_id": "scene001"}},
        ],
    }
    paragraphs, plain, _ = project_doc(doc)
    assert [item["type"] for item in paragraphs] == ["heading", "horizontalRule"]
    assert plain == "Tên\n\n* * *"


def test_validate_doc_rejects_bad_or_duplicate_ids():
    with pytest.raises(ValueError, match="invalid_paragraph_id"):
        validate_doc(
            {"type": "doc", "content": [{"type": "paragraph", "attrs": {"paragraph_id": "x"}}]}
        )
    with pytest.raises(ValueError, match="duplicate_paragraph_id"):
        validate_doc(
            {
                "type": "doc",
                "content": [
                    {"type": "paragraph", "attrs": {"paragraph_id": "same0001"}},
                    {"type": "heading", "attrs": {"paragraph_id": "same0001"}},
                ],
            }
        )
