# S01 — Khung monorepo

Trạng thái: done. Tính năng: nền tảng. Phụ thuộc: S00.

## Mục tiêu

Repo có cấu trúc `fe/`, `be/`, `ai/` (sau thêm `desktop/`) theo [folder-architecture.vi.md](../folder-architecture.vi.md) §3, với một lockfile Python (uv) và một lockfile JS (pnpm).

## Việc cần làm

- [x] `pyproject.toml` gốc: `[tool.uv.workspace] members = ["be", "ai"]`, `[tool.uv.sources] writestory-ai = { workspace = true }`, nhóm dev (pytest, pytest-asyncio, httpx, ruff), cấu hình ruff và pytest.
- [x] `.python-version` = `3.14`.
- [x] `package.json` gốc (scripts điều phối) + `pnpm-workspace.yaml` (`fe`; thêm `desktop` ở S07).
- [x] `.gitignore`: `.venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `fe/dist/`, `desktop/src-tauri/target/`, build PyInstaller, `data/*`.
- [x] `.editorconfig` (UTF-8, LF, 4 space cho Python, 2 space cho TS/JSON/MD).
- [x] `README.md` gốc: giới thiệu, cấu trúc, lệnh nhanh.
- [x] `contracts/` (OpenAPI sinh ở S05), `tools/` (scripts).

## Lệnh

```bash
uv sync
```

```bash
pnpm install
```

## Tiêu chí xong

- `uv sync` tạo `.venv` ở gốc và `uv.lock` (cần S00).
- `pnpm install` tạo `pnpm-lock.yaml`, không có lockfile npm/yarn.

## Ghi chú

Không tạo trước thư mục rỗng cho mọi module (Arch §11); chỉ tạo khi bước tương ứng cần.
