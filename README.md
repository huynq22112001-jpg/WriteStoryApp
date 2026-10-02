# WriteStoryApp

Ứng dụng desktop viết truyện bằng AI, chạy cục bộ. Repository gồm frontend React, backend FastAPI và package AI Python; Tauri được bổ sung ở giai đoạn desktop.

## Công cụ cần có

- Git
- Python 3.14 và [uv](https://docs.astral.sh/uv/)
- Node.js 22.16 trở lên và pnpm 10.33.2

## Cài đặt

```powershell
uv sync
pnpm install
```

## Chạy phát triển

```powershell
pnpm dev
```

Lệnh này chạy backend ở `http://127.0.0.1:8765` và frontend ở `http://localhost:5173/#/system`. Nhấn `Ctrl+C` để dừng cả hai.

Có thể chạy riêng từng phần:

```powershell
uv run python -m writestory_be --dev
pnpm --filter fe dev
```

## Kiểm tra và build

```powershell
uv run pytest ai/tests be/tests -q
uv run ruff check ai be tools
pnpm --filter fe typecheck
pnpm --filter fe test
pnpm --filter fe build
```

## Cấu trúc repository

- `ai/` — contracts, provider và workflow AI.
- `be/` — API FastAPI, dữ liệu và job nền.
- `fe/` — giao diện React/TypeScript.
- `desktop/` — ứng dụng Tauri và tích hợp backend desktop.
- `contracts/` — OpenAPI sinh từ backend.
- `docs/` — kế hoạch, spec tính năng, bước triển khai và prompt.
- `tools/` — tiện ích phát triển và hợp đồng API.

## Tài liệu

Xem [docs/README.md](docs/README.md) để đọc kế hoạch, kiến trúc, đặc tả tính năng, luồng test và tiến độ triển khai.
