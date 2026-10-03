from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from typing import Any

from jinja2 import StrictUndefined, TemplateNotFound
from jinja2.filters import do_tojson
from jinja2.loaders import BaseLoader
from jinja2.sandbox import SandboxedEnvironment

from writestory_ai.languages.vi.length import count_syllables


class PromptIntegrityError(ValueError):
    pass


def _field(item, name: str):
    return getattr(item, name) if hasattr(item, name) else item[name]


class _ManifestLoader(BaseLoader):
    def __init__(self, language: str, manifest: dict[str, dict[str, Any]]):
        self.language = language
        self.manifest = manifest

    def get_source(self, environment, template):
        entry = self.manifest.get(template)
        if entry is None:
            raise TemplateNotFound(template)
        source = (
            files(f"writestory_ai.languages.{self.language}")
            .joinpath("prompts", entry["file"])
            .read_text(encoding="utf-8")
        )
        actual = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if actual != entry["sha256"]:
            raise PromptIntegrityError(f"Prompt checksum mismatch: {template}")
        return source, f"{self.language}/prompts/{entry['file']}", lambda: True


class PromptRegistry:
    def __init__(self, language: str = "vi") -> None:
        root = files(f"writestory_ai.languages.{language}").joinpath("prompts")
        raw = json.loads(root.joinpath("manifest.json").read_text(encoding="utf-8"))
        self.manifest = {item["id"]: item for item in raw["prompts"]}
        self.environment = SandboxedEnvironment(
            loader=_ManifestLoader(language, self.manifest),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.environment.globals.clear()
        self.environment.filters.clear()
        self.environment.filters.update(
            {
                "paragraphs": lambda values: "\n".join(
                    f"[p:{_field(item, 'paragraph_id')}] {_field(item, 'text')}" for item in values
                ),
                "units": count_syllables,
                "bullets": lambda values: "\n".join(f"- {item}" for item in values),
                "tojson": do_tojson,
            }
        )

    def render(self, prompt_id: str, **variables: Any) -> str:
        if prompt_id not in self.manifest:
            raise KeyError(f"Unknown prompt id: {prompt_id}")
        return self.environment.get_template(prompt_id).render(**variables)

    def prompt_version(self, prompt_id: str) -> str:
        item = self.manifest[prompt_id]
        return f"{prompt_id}@{item['version']}#{item['sha256'][:8]}"
