# Trạng thái triển khai

Cập nhật: 02/10/2026. File này ghi **đúng sự thật** những gì đã có trong repo, để các cửa sổ làm việc khác biết bắt đầu từ đâu.

## 1. Tài liệu kế hoạch – đã xong

| Hạng mục | Vị trí | Trạng thái |
|---|---|---|
| Kế hoạch tổng + bảng quyết định D1–D45 | [implementation-plan.vi.md](../implementation-plan.vi.md) §1–§24 | Xong |
| Kiến trúc thư mục | [folder-architecture.vi.md](../folder-architecture.vi.md) | Xong |
| Giao diện + thư viện React | [ui-design.vi.md](../ui-design.vi.md) | Xong |
| Rà soát + kiểm chứng web | [review-and-optimization.vi.md](../review-and-optimization.vi.md) | Xong |
| 15 tính năng MVP × (README/be/fe/ai) | [features/](../features/README.md) | Xong (60 file) |
| 17 luồng test, 286 kịch bản | [tests/](../tests/README.md) | Xong |
| 11 bước R0 (S00–S10) | [steps/](./README.md) | Xong |
| Prompt triển khai: 136 file, mỗi file một prompt | [prompts/](../prompts/README.md) | Xong |

## 2. Code đã viết (bản nháp base – CHƯA kiểm chứng)

Code được viết trước khi chốt kế hoạch. **Chưa chạy bất kỳ test nào.** Máy dev chưa có uv/Python nên BE/AI chưa chạy được; FE đã `pnpm install` nhưng chưa chạy typecheck/test/build. Coi toàn bộ là **bản nháp cần kiểm chứng** (prompt [P001](../prompts/P001-cai-moi-truong-uv-python.md) → [P002](../prompts/P002-kiem-chung-ai-base.md), [P003](../prompts/P003-kiem-chung-be-base.md), [P004](../prompts/P004-kiem-chung-fe-base.md)).

### Gốc repo (S01)

| File | Nội dung |
|---|---|
| `pyproject.toml` | uv workspace (`be`, `ai`), nhóm dev (pytest, pytest-asyncio, httpx, ruff), cấu hình pytest/ruff |
| `.python-version` | `3.14` |
| `package.json`, `pnpm-workspace.yaml` | pnpm workspace (`fe`), script điều phối |
| `.gitignore`, `.editorconfig` | Bỏ qua build/venv/node_modules/data; định dạng chung |
| `pnpm-lock.yaml`, `node_modules/` | Đã tạo bởi `pnpm install` |

Chưa có: `uv.lock`, `.venv/`, `README.md` gốc, `contracts/openapi.json`.

### AI – `ai/` (S02)

| File | Nội dung |
|---|---|
| `contracts/errors.py` | `AIError` + lớp con, `code` trùng `ErrorCode` BE |
| `contracts/generation.py` | `Message`, `GenerationRequest` (effort), `TextDelta`, `StreamDone`, `GenerationResult` |
| `contracts/usage.py`, `contracts/events.py` | `Usage`, `StepProgress`, `TokenDelta` |
| `ports/provider.py`, `ports/progress.py` | `TextProvider`, `ProgressSink` (Protocol) |
| `providers/mock.py`, `providers/collect.py` | Mock provider (latency, tốc độ, chuỗi lỗi, refusal, cắt, mất kết nối), gom stream |
| `languages/base.py`, `registry.py`, `vi/{normalizer,length,search}.py` | `LanguagePack`, gói `vi`: NFC, đếm âm tiết, fold tìm kiếm (bỏ dấu + `đ→d`) |
| `tests/unit/*` (3 file) | Gói vi, mock provider, AI không import BE |

### BE – `be/` (S03)

| File | Nội dung |
|---|---|
| `__main__.py`, `bootstrap/runtime.py` | Chế độ desktop (stdin `BootstrapConfig` → `ready`) và `--dev` (cổng 8765, token `dev-token`) |
| `bootstrap/protocol.py`, `context.py`, `lifecycle.py`, `logging_setup.py` | Giao thức, `Runtime`, khóa `db/.backend.lock`, kênh NDJSON, theo dõi stdin EOF, log che token |
| `core/{ids,clock,errors}.py` | UUIDv7, ISO UTC, `ErrorCode`/`ErrorAction`/`AppError` |
| `api/{errors,request_id,security,dependencies,events_schema,streams}.py` | `ErrorResponse`, `X-Request-Id`, Host/Origin/token, envelope, SSE `/v1/events` |
| `jobs/events.py` | `EventBus` chế độ RAM (seq, replay, replay_gap, cắt client chậm, transient) |
| `modules/system/router.py` | `GET /v1/health`, `POST /v1/system/shutdown` |
| `modules/dev/router.py` | `POST /v1/dev/mock-runs` (nhiều truyện mock stream song song) |
| `infrastructure/db/engine.py` | Engine `sqlite+aiosqlite`, pragma WAL/FULL/foreign_keys/busy_timeout |
| `main.py` | `create_app(runtime)` không side effect |
| `tests/*` (6 file) | Bảo mật, lỗi, health, EventBus, SSE qua uvicorn thật, bootstrap tiến trình |
| `tools/contracts/export_openapi.py` | Xuất OpenAPI (S05) |

Chưa có: Alembic/migration, bảng nào, writer queue, unit of work.

### FE – `fe/` (S04)

| File | Nội dung |
|---|---|
| `package.json`, `tsconfig.json`, `vite.config.ts`, `vitest.config.ts`, `index.html`, `.env.development` | Vite 8, React 19, TS 5.9, Tailwind 4, Vitest 5 |
| `app/{App,providers,router}.tsx`, `app/layouts/AppShell.tsx` | TanStack Router (hash), React Query, khung trang |
| `shared/api/{types,errors,client,sse}.ts` | Kiểu tạm, `ApiError`, client có token/Idempotency-Key, parser SSE + tự nối lại |
| `shared/desktop/bridge.ts` | Lấy URL/token backend (dev từ env; Tauri ở S07) |
| `shared/i18n/` | i18next, chỉ `vi` (common, errors) |
| `features/library/`, `features/system/` | Thư viện rỗng; trang Trạng thái hệ thống (health, sự kiện, mock 3 truyện) |
| `*.test.ts(x)` (3 file) | Parser SSE, lỗi API, trang thư viện |

Chưa có: shadcn/ui, font Fontsource, generated API types, Tauri bridge.

### Lệch so với spec cần lưu ý khi kiểm chứng

- `MockFailure.kind="server"` sinh mã `PROVIDER_SERVER_ERROR` – chưa có trong `ErrorCode` của BE (§24 D14 có nhắc 5xx). Thêm vào `ErrorCode` hoặc đổi tên.
- `EventEnvelope.payload` đang là object tự do; payload có kiểu theo `type` làm ở F01/F10–F14.
- `GET /v1/jobs/{id}/events` chưa có (chưa có bảng jobs).

## 3. Tiến độ theo kế hoạch

| Giai đoạn | Việc | Trạng thái |
|---|---|---|
| R0 | S00 môi trường | Node/pnpm/Rust có; **thiếu uv + Python 3.14** |
| R0 | S01 khung monorepo | Code đã viết, chưa `uv sync` |
| R0 | S02 base AI | Code nháp, **chưa chạy test** |
| R0 | S03 base BE | Code nháp, **chưa chạy test** |
| R0 | S04 base FE | Code nháp, đã cài deps, **chưa typecheck/test/build** |
| R0 | S05 OpenAPI → TS | Có script export, chưa chạy |
| R0 | S06 chạy dev | Có `--dev` + `.env.development`, chưa thử |
| R0 | S07 Tauri, S08 editor/IME, S09 đóng gói, S10 kết thúc R0 | Chưa làm |
| R1 | F02, F03, F05, F04, F07 | Chưa làm |
| R2 | F08–F14, F06 | Chưa làm |

Ước lượng hoàn thành theo checklist: tài liệu ~100%; R0 ~25% (khung + nháp base, chưa kiểm chứng); R1/R2 0%.
