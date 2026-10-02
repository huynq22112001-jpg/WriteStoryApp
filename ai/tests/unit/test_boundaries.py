from pathlib import Path

AI_SRC = Path(__file__).resolve().parents[2] / "src" / "writestory_ai"


def test_ai_package_does_not_import_backend():
    """AI không phụ thuộc ngược BE, FastAPI hay ORM (folder-architecture §6)."""
    forbidden = ("writestory_be", "fastapi", "sqlalchemy")
    offenders = [
        f"{path.relative_to(AI_SRC)}: {name}"
        for path in AI_SRC.rglob("*.py")
        for name in forbidden
        if f"import {name}" in (text := path.read_text(encoding="utf-8"))
        or f"from {name}" in text
    ]
    assert offenders == []
