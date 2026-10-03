import pytest
from jinja2 import UndefinedError
from jinja2.exceptions import SecurityError

from writestory_ai.prompts.loader import PromptIntegrityError, PromptRegistry


def test_manifest_prompt_renders_and_versions():
    prompts = PromptRegistry()
    assert "trợ lý sáng tác" in prompts.render("common.system")
    rendered = prompts.render(
        "longform.chapter_context",
        chapter_no=4,
        paragraphs=[{"paragraph_id": "abc12345", "text": "Chào."}],
    )
    assert "[p:abc12345] Chào." in rendered
    assert prompts.prompt_version("common.system").startswith("common.system@1#")
    assert len(prompts.manifest) == 26
    for prompt_id in prompts.manifest:
        prompts.environment.get_template(prompt_id)


def test_unknown_prompt_and_missing_variable_are_rejected():
    prompts = PromptRegistry()
    with pytest.raises(KeyError):
        prompts.render("user.supplied")
    with pytest.raises(UndefinedError):
        prompts.render("longform.chapter_context", chapter_no=1)


def test_checksum_mismatch_is_rejected(monkeypatch):
    prompts = PromptRegistry()
    prompts.manifest["common.system"]["sha256"] = "0" * 64
    with pytest.raises(PromptIntegrityError):
        prompts.render("common.system")


def test_story_text_is_data_and_sandbox_blocks_private_attributes():
    prompts = PromptRegistry()
    rendered = prompts.render(
        "longform.chapter_context",
        chapter_no=2,
        paragraphs=[{"paragraph_id": "abcd1234", "text": "{{ 7 * 7 }}"}],
    )
    assert "{{ 7 * 7 }}" in rendered
    with pytest.raises(SecurityError):
        prompts.environment.from_string("{{ value.__class__ }}").render(value=object())
