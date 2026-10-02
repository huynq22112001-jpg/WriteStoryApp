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

## 2. Code nền và kết quả kiểm chứng

Code nền được viết trước khi chốt kế hoạch. Môi trường P001 đã cài; P002 AI, P003 BE, P004 FE và P005 đã qua xác minh. OpenAPI và types TypeScript (P006–P007) cũng đã xuất ổn định. Xem tiến độ chi tiết bên dưới.

### Gốc repo (S01)

| File | Nội dung |
|---|---|
| `pyproject.toml` | uv workspace (`be`, `ai`), nhóm dev (pytest, pytest-asyncio, httpx, ruff), cấu hình pytest/ruff |
| `.python-version` | `3.14` |
| `package.json`, `pnpm-workspace.yaml` | pnpm workspace (`fe`), script điều phối |
| `.gitignore`, `.editorconfig` | Bỏ qua build/venv/node_modules/data; định dạng chung |
| `pnpm-lock.yaml`, `node_modules/` | Đã tạo bởi `pnpm install` |

Chưa có: `README.md` gốc, `contracts/openapi.json`.

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
| `jobs/events.py` | `EventBus` RAM + DB (outbox sau commit, watermark bền, replay/replay_gap), flush/preview còn chờ |
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
| R0 | S00 môi trường | uv 0.12.22 + CPython 3.14.8 managed đã cài; C++ Build Tools chưa xác nhận |
| R0 | S01 khung monorepo | Code đã viết; `uv sync` đã tạo `.venv/` và `uv.lock` |
| R0 | S02 base AI | 25 test pass, Ruff pass, không import BE |
| R0 | S03 base BE | 45 test pass hiện tại; Ruff pass; đã thêm `PROVIDER_SERVER_ERROR` |
| R0 | S04 base FE | P004 done: typecheck, 10 test và build pass sau khi khóa phiên bản đáp ứng minimumReleaseAge |
| R0 | S05 OpenAPI → TS | P006–P007 done: export ổn định, contract test và script check_contracts pass |
| R0 | S06 chạy dev | P008 done: `pnpm dev` chạy BE/FE; UI báo health, stream mock ba truyện và hiện banner khi dừng BE |
| R0 | S07 Tauri | P009 scaffold + single-instance và P010 data-root/instance lock đã xong; P011–P013 backend lifecycle/FE còn lại |
| R0 | S08 editor/IME, S09 đóng gói, S10 kết thúc R0 | Chưa làm |
| R1 | BE nền dữ liệu/API | P101–P113 xong; P114–P129 và các làn FE/AI còn lại chưa hoàn thành |
| R1 | F03, F05, F04, F07 | Chưa làm |
| R2 | F08–F14, F06 | Chưa làm |

Tiến độ prompt R0: P001–P010 đã `done`; P011–P020 còn lại chưa hoàn thành. R1 làn BE: P101–P113 đã xong; phần BE tiếp theo bắt đầu từ P114.

### Cập nhật P113 (02/10/2026)

- Thêm API vault/secrets gồm tạo, trạng thái, mở/khóa, đổi mật khẩu, reset, đổi mode và CRUD secret; dùng `SecretStr`, lỗi không phản hồi giá trị secret, và có throttle mở vault.
- Lưu `vault.mode` cùng `secrets.index` vào bảng `settings`; index chỉ lưu metadata. Đồng bộ lại index sau khi mở vault, phát `vault.status`, báo `waiting_jobs` cần mở vault.
- Thêm error codes vault, xuất OpenAPI và đồng bộ TypeScript types.
- Kiểm chứng: toàn bộ BE `65 passed`; Ruff pass; `check_contracts.py` pass; `git diff --check` pass.

### Cập nhật P112 (02/10/2026)

- Thêm `SessionSecretStore` chỉ giữ dữ liệu trong RAM, `SecretStore` hợp nhất session/vault và callback `on_change`.
- Đăng ký secret vào bộ lọc log dùng chung; secret được thêm sau khi khởi động logging vẫn được che.
- Kiểm thử mất key session sau khi tạo store mới và che log; 5 test secrets pass, Ruff pass.

### Cập nhật P111 (02/10/2026)

- Thêm `cryptography>=44`; vault AES-256-GCM, KDF Argon2id với fallback Scrypt, AAD chuẩn hóa, salt/nonce ngẫu nhiên, ghi tệp nguyên tử và khóa truy cập đồng thời.
- Thêm kiểm thử round-trip, đổi mật khẩu, mật khẩu sai, file JSON hỏng, nonce không trùng, không ghi plaintext; 3 test pass. Ruff secrets pass.

### Cập nhật P101–P110 (02/10/2026)

- P101: Alembic async gắn DB vào data-root, batch mode và naming convention cho constraint.
- P102: migration `0001_baseline` cùng ORM cho settings, jobs, job_steps, job_events, idempotency_records, work_locks, assets.
- P103: migration tự động trước khi bind, backup `VACUUM INTO`, marker DB, kiểm tra revision mới hơn/mất DB; health trả schema revision.
- P104: writer queue tuần tự, UnitOfWork, event outbox cùng transaction và guard cấm gọi ngoài transaction ghi.
- P105: khóa truyện có lease 60 giây, heartbeat, chờ lấy khóa, dọn lease hết hạn và fencing khi commit. `work_locks` đã có trong baseline F02 nên không tạo migration trùng.
- P106: khôi phục job/step `running` thành `interrupted`, xóa lock và file tạm; retention theo lô cho event quá 90 ngày, idempotency hết hạn và backup cũ. Phát `backend.notice` sau ready nếu có job bị gián đoạn.
- P107: FTS5 dùng `search_fold` của AI, chuẩn hóa an toàn query, đồng bộ insert/update/delete qua trigger, BM25 và rebuild; migration tạo chỉ mục văn bản + trigram.
- P108: EventBus đọc lại event lưu DB theo seq, phát event từ UoW sau commit, lọc replay gap sau retention; SSE đăng ký trước rồi replay tới watermark.
- P109: thêm `stream.tail`, endpoint lọc `/v1/jobs/{job_id}/events`, payload models và xuất lại OpenAPI.
- P110: canonical SHA-256 cho method/path/body; service replay response cũ, conflict khi body khác, lưu kết quả trong cùng UoW.
- Kiểm chứng P101–P107: `uv run --no-sync pytest be/tests -q` — 51 passed; P108: 52 passed; P109: 53 passed; P110: 55 passed; Ruff BE — pass.

### Cập nhật P004 (02/10/2026)

- Đã thêm bản dịch `PROVIDER_SERVER_ERROR` trong `fe/src/shared/i18n/vi/errors.json`.
- Hạ `@asamuzakjp/dom-selector` xuống `9.2.2` qua override workspace và khóa `@types/node` ở `26.6.3`; pnpm xác nhận lockfile qua kiểm tra supply-chain mà không nới `minimumReleaseAge`.
- P004: `pnpm --filter fe typecheck` pass; 3 test files / 10 tests pass; `pnpm --filter fe build` pass.

### Cập nhật P006–P007 (02/10/2026)

- P006: export OpenAPI hai lần cho SHA-256 giống nhau; contract snapshot test pass.
- P007: sinh `schema.d.ts`, chuyển `types.ts` sang re-export schema; `python tools/contracts/check_contracts.py` pass và không làm thay đổi artifact.

### Cập nhật P008 (02/10/2026)

- Thêm `pnpm dev`, script gốc chạy BE và Vite song song, có tiền tố `[be]` / `[fe]` và dừng hai tiến trình khi kết thúc.
- Smoke tại `http://localhost:5173/#/system`: health báo đã kết nối; nút mock stream nội dung cho ba truyện; khi dừng backend, FE hiện “Mất kết nối – đang nối lại…”. Đã dừng các máy chủ sau kiểm tra.

### Cập nhật P009 (02/10/2026)

- Thêm workspace desktop, Tauri CLI, config dev/build với CSP và capability tối thiểu, icon Windows, Rust shell và single-instance (hiện/show/focus cửa sổ cũ).
- `cargo check` pass; `pnpm --filter desktop tauri dev` biên dịch và chạy `writestory-app.exe`; chạy lần hai giữ một tiến trình app. Chưa spawn backend ở P009.

### Cập nhật P010 (02/10/2026)

- Thêm phân giải data-root Windows/macOS, ghi marker và pointer nguyên tử, kiểm tra quyền ghi, thư mục cloud sync, network drive (UNC/Windows drive type và macOS `statfs`), macOS App Translocation, cùng `WRITESTORY_DATA_ROOT` chỉ khi build debug.
- Thêm khóa OS độc quyền `.instance.lock` bằng `fs4` và kiểu trạng thái khởi động/event `boot:state`.
- `cargo fmt` và `cargo test` trên Windows pass: 8 test. Nhánh macOS `statfs` chưa được chạy trên host Windows. Cảnh báo dead-code hiện tại do tích hợp các module vào boot flow thuộc P011/P012.

### Cập nhật P001–P005 (02/10/2026)

- P001: uv 0.12.22, CPython 3.14.8 do uv quản lý; `uv sync` tạo `.venv/` và `uv.lock`; `uv run python --version` trả Python 3.14.8.
- P002: `uv run pytest ai/tests -q` — 25 passed; `uv run ruff check ai` — pass; test ranh giới AI có trong bộ test.
- P003: `uv run pytest be/tests -q` — 38 passed; `uv run ruff check be tools` — pass. Đã thêm fixture chung cho BE tests và `PROVIDER_SERVER_ERROR` (HTTP 502, retryable) vào ErrorCode.
- P005: backend `--dev` trả health 200; thiếu token trả 401 `UNAUTHORIZED`; mock-runs trả 202 và SSE nhận `token.delta` từ cả ba truyện; server đã dừng.
