"""Xuất OpenAPI từ BE ra `contracts/openapi.json` (F01 be.md §D, steps/S05).

`create_app(None)` không mở vault, không migrate, không chạy job nên chạy được ở CI.
"""

import json
from pathlib import Path

from writestory_be.main import create_app

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "contracts" / "openapi.json"


def main() -> None:
    schema = create_app().openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Đã ghi {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
