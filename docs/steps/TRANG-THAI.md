# Trạng thái triển khai

Cập nhật: 03/10/2026. File này ghi **đúng sự thật** những gì đã có trong repo, để các cửa sổ làm việc khác biết bắt đầu từ đâu.

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
| R0 | S00 môi trường | uv 0.12.22 + CPython 3.14.8 managed; pnpm dependencies đồng bộ; VS C++ workload + WebView2 có sẵn |
| R0 | S01 khung monorepo | Code đã viết; `uv sync` đã tạo `.venv/` và `uv.lock` |
| R0 | S02 base AI | 25 test pass, Ruff pass, không import BE |
| R0 | S03 base BE | 45 test pass hiện tại; Ruff pass; đã thêm `PROVIDER_SERVER_ERROR` |
| R0 | S04 base FE | P004 done: typecheck, 10 test và build pass sau khi khóa phiên bản đáp ứng minimumReleaseAge |
| R0 | S05 OpenAPI → TS | P006–P007 done: export ổn định, contract test và script check_contracts pass |
| R0 | S06 chạy dev | P008 done: `pnpm dev` chạy BE/FE; UI báo health, stream mock ba truyện và hiện banner khi dừng BE |
| R0 | S07 Tauri | P009 scaffold, P010 data-root/instance lock, P011 spawn/readiness, P012 shutdown/commands và P013 BootGate đã xong |
| R0 | S08 editor/IME | P014–P016 implementation xong; checklist IME thủ công chưa chạy trên WebView nào |
| R0 | S09 đóng gói | Windows onedir + NSIS offlineInstaller build xong; clean-machine install và macOS build chưa thử |
| R0 | S10 kết thúc R0 | P020 đã nghiệm thu bằng chứng: 1/6 tiêu chí đạt, 5 chưa đạt/chưa có bằng chứng; xem S10 |
| R1 | BE nền dữ liệu/API | P101–P129 done; BE tests 104 passed, Ruff và contract check pass |
| R1 | F03, F05, F04, F07 | FE P150–P167 done; unit 50 passed, Playwright 7 passed; typecheck/build pass |
| R1 | AI adapter/limiter | P118–P121 done; AI suite 105 passed |
| R2 | F08–F14, F06 | AI P201–P220 đã có implementation nền; F08–F10 chưa verified, BE/FE và F11–F14/F06 chưa làm |

Tiến độ prompt R0: P001–P013 đã `done`; P014–P020 còn lại chưa hoàn thành. R1: P101–P129 và P150–P167 đã `done`; xem các giới hạn IME thủ công bên dưới.

### Cập nhật P013 (03/10/2026)

- Thêm bridge Tauri/web mock, type BootState/BackendSession theo JSON Rust, hook/store và BootGate; đăng ký event trước snapshot để không ghi đè trạng thái mới hơn.
- Thêm màn khởi động, chọn data-root, translocated, lỗi khởi động, backend crash; thêm ConnectionBanner 2 giây và status bar.
- Dùng một event bus SSE chung cho app và test crash → ready để xóa/cài lại session trong RAM.
- FE: `pnpm --filter fe typecheck` pass; test 8 file / 27 passed; `pnpm --filter fe build` pass.

### Cập nhật P012 (03/10/2026)

- Thêm các Tauri commands cho boot state, chọn/xác nhận data-root, lấy backend session, restart, mở logs và thoát app; token chỉ trả qua `get_backend_session`.
- `ExitRequested` ngăn thoát tức thời, gọi API shutdown, chờ backend dừng rồi kill nếu quá hạn; `Exit` có nhánh dự phòng. Windows Job Object giữ backend tree.
- Thử đóng cửa sổ: log ghi `ShuttingDown`, app và tiến trình uv/Python đều thoát. Thử kill `writestory-app.exe`: uv và cả hai tiến trình Python thoát theo.
- `cargo test` — 13 passed. Chưa thử Cmd+Q trên macOS hoặc installer đóng gói.

### Cập nhật P011 (03/10/2026)

- Rust tự chạy `uv run python -m writestory_be` trong chế độ dev, gửi BootstrapConfig một dòng và giữ stdin mở; token ngẫu nhiên 32 byte chỉ giữ trong tiến trình.
- Đọc NDJSON progress/ready/fatal; drain stderr vào `logs/backend-stderr.log` và ring buffer 200 dòng; timeout readiness 60 giây được gia hạn theo progress; health check xác thực token, protocol version và data_id trước phase `ready`.
- Theo dõi backend exit, phát `backend_crashed`; Windows gán backend vào Job Object `KILL_ON_JOB_CLOSE`.
- `cargo test` — 13 passed; `tauri dev` smoke trên data-root tạm — backend migration xong, phase `Ready`, health check thành công. Đã dừng app và backend sau smoke.
- Restart command được bổ sung ở P012; smoke kill-on-close trên installer đóng gói còn chờ P018.

### Cập nhật P114 (03/10/2026)

- Thêm API onboarding đọc/cập nhật bước, hoàn tất/bỏ qua, lưu `onboarding.state` vào `settings`, kiểm revision và tự hoàn tất khi đã có tác phẩm.
- Test tích hợp trạng thái ban đầu, cập nhật bước, revision cũ, restart, bỏ qua và tự hoàn tất: `2 passed`; toàn bộ BE `67 passed`; Ruff BE pass.

### Cập nhật môi trường (03/10/2026)

- Cài uv 0.12.22 vào `C:\Users\HorusPC\.local\bin`, CPython 3.14.8 do uv quản lý; `uv sync --locked` hoàn tất.
- `pnpm install --frozen-lockfile` đã xác nhận dependency FE/Desktop đồng bộ; Node 24.15.0, pnpm 10.33.2, Rust 1.98.0 đã có.
- Xác nhận Visual Studio Community 2026 có C++ workload, WebView2 Runtime có sẵn; `cargo check --manifest-path desktop/src-tauri/Cargo.toml` pass.

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

### Cập nhật P014–P020 (03/10/2026)

- P014: thêm Tiptap v3 editor `/editor-spike`, `paragraph_id` 8 ký tự, unique ID extension và test split/merge giữ ID đúng; `prosemirror-view` đã pin tối thiểu theo override.
- P015: port `normalize_text`/`count_syllables` sang TypeScript; paste text/HTML NFC; editor hiện âm tiết và ký tự. Ca Python tương ứng được đối chiếu bằng tests.
- P016: thêm nút bold/italic và [checklist IME thủ công](../tests/manual/ime-checklist.md). Không có ô IME nào được đánh dấu đạt; chưa chạy trên WebView2/WKWebView.
- P017: PyInstaller 6.22.3 onedir build xong; backend frozen qua migrations và phát `ready`. Build script dùng nhóm `build` của `writestory-be`.
- P018: release Rust spawn backend từ Tauri resources; Windows NSIS `offlineInstaller` build xong (230.11 MiB). Một smoke trên host đạt ready: 6.74 s lần đầu, 1.56 s lần sau; sau 5 s idle RSS 26.6 MiB app + 110.9 MiB backend. Chưa cài trên máy sạch.
- P019: script codesign Mach-O và hướng dẫn DMG có sẵn; `bash -n` pass, shellcheck không cài; chưa chạy trên Mac.
- P020: ADR-001–004 và S10 được cập nhật. S10: chỉ đóng app sạch backend đạt đủ bằng chứng (1/6); mock SSE đã smoke nhưng editor không-block chưa đo; clean install, hai-WebView IME và App Translocation macOS chưa có bằng chứng.
- Bộ nghiệm thu: `uv run pytest ai/tests be/tests -q` — 141 passed; FE typecheck pass, 10 files / 36 tests pass, production build pass; `cargo fmt --check` và `cargo test` — 13 passed. Build FE còn cảnh báo chunk >500 kB; Rust có 2 cảnh báo dead-code.

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

### Cập nhật P201 (03/10/2026)

- Mở rộng LanguagePack với deterministic_checks, slop_list, genre_presets và prompts_dir; thêm contract LanguageFinding/CheckContext, dữ liệu xưng hô/động từ thoại/âm tiết/cụm sáo và đủ 8 preset thể loại.
- Bộ âm tiết hiện là seed viết tay tối thiểu, chưa phải từ điển đầy đủ; nguồn và giới hạn được ghi trong file dữ liệu.
- Kiểm chứng: uv run --no-sync pytest ai/tests -q — 55 passed.

### Cập nhật R1 tiếp tục (03/10/2026)

- Hoàn tất P122–P129: provider CRUD/discovery/roles/model resolver/limiter; CRUD chương, working copy, snapshot có revision guard, diff/restore, projection paragraph, khóa nền, FTS; chèn/xóa chương đổi số qua bước tạm để không va chạm unique index.
- FE: thêm error action và mở vault từ action, protocol/provider test và discovery, effort theo capability, giới hạn/ngân sách/cấu hình viết toàn app, wizard tạo truyện 7 bước lưu tiến độ, redirect onboarding, lọc thư viện, kéo thả model/chương, cột workspace kéo giãn và phím tắt focus.
- Trạng thái prompt R1 trong `docs/prompts/README.md`: P101–P129 và P150–P167 `done`. FE hoàn tất onboarding/vault, wizard có zod + react-hook-form và mở lại bản nháp, settings provider/model/roles/limits, editor autosave với IME composition wait, khóa nền/tạm dừng, xung đột và history diff/restore. Bản model có thể đổi tên trực tiếp.
- Kiểm chứng cuối: BE 104 passed; AI 105 passed; FE typecheck pass, unit 17 files / 50 tests, Playwright 7 passed, production build pass; Ruff BE và `tools/contracts/check_contracts.py` pass. Build còn cảnh báo bundle JS lớn hơn 500 kB.
- Checklist IME-01…IME-12 vẫn cần chạy thủ công trên Windows WebView2 và macOS WKWebView; chưa ghi nhận kết quả thủ công.


### Cập nhật P121 và P201–P220 (03/10/2026)

- Đã có implementation nền cho LanguagePack/checks, state contracts/reducer/validator, ParagraphOps, context, token tail, summaries, các bước longform, pipeline callback và outline review. P201–P203, P205–P214 cùng P121 được đánh dấu done; P204, P207–P208 và P215–P220 đang doing vì còn thiếu một phần tiêu chí chi tiết.
- Mở rộng LanguagePack/checks và prompt loader Jinja sandbox với manifest checksum. Jinja2 được khai báo trong dependency và lockfile.
- Kiểm chứng: `uv run --no-sync pytest ai/tests -q` — 77 passed; `uv run --no-sync ruff check ai` — pass.
- Giới hạn còn lại: `syllables.txt` là seed viết tay, chưa phải từ điển đủ; bộ kiểm tra tiếng Việt và prompt catalogue là bản khởi đầu, chưa có dữ liệu/ngưỡng đo cho mọi trường hợp trong F08. P201–P220 được triển khai ở mức nền AI; cần nghiệm thu tích hợp với BE/FE và dữ liệu mẫu trước khi coi F08–F10 verified.

### Rà soát tiếp P204, P207–P220 (03/10/2026)

- Cải thiện dò Telex/VNI sót: chỉ cảnh báo khi giải mã thành âm tiết có trong seed; thêm gợi ý sửa và test các trường hợp đúng/sai. Slop nâng mức theo spec; chính tả hỏi/ngã giữa hai âm tiết hợp lệ vẫn không kiểm tra theo D45.
- State validator bổ sung so bằng chứng candidate sau NFC, xử lý thêm trùng fact và state nhân vật theo thứ tự op; các khoảng trống về bộ fixture V01–V15 vẫn cần hoàn thiện.
- Reviewer gộp finding xác định/LLM, giữ trạng thái chờ xác nhận và loại finding bị bác. Pipeline từ chối thiếu stage/điểm resume sai; outline review chỉ gọi evaluator đúng mốc và không sửa event đã khóa.
- Kiểm chứng ban đầu: `uv run --no-sync pytest ai/tests -q` — 104 passed; `uv run --no-sync ruff check ai` — pass.
- Trạng thái P204, P207–P208 và P215–P220 vẫn `doing`: từ điển âm tiết chưa đủ nguồn/phủ rộng, ma trận test V01–V15 và contract test pipeline chưa đạt phạm vi prompt. Không coi bộ AI F08–F10 là đã nghiệm thu tích hợp.
- Vòng sửa validator theo thứ tự op: kiểm thêm thời gian tiến rồi lùi trong cùng delta và event bị đánh dấu done lặp. Kiểm chứng lại: `uv run --no-sync pytest ai/tests -q` — 105 passed; Ruff pass; `git diff --check` pass (Git chỉ cảnh báo chuẩn CRLF hiện có).
- Kiểm tra AI chạy lại trong lượt R1: 103 passed / 1 failed tại `test_pipeline_resume_runs_from_requested_checkpoint_and_requires_all_stages`; trạng thái AI R2 cần đối chiếu lại trước khi đánh dấu xanh.

### Hoàn tất P207 (03/10/2026)

- Hoàn thiện kiểm tra V01–V08 với ca hợp lệ và không hợp lệ; sửa validator đọc đúng Pydantic op models, xét được fact khai báo trước trong delta và chỉ báo lộ bí mật khi `knowledge_uses` xảy ra trước `character.learn`.
- Quote trong `KnowledgeUse` được kiểm tra sau chuẩn hóa NFC; reducer giữ thuần và trả state hash chuẩn hóa như spec.
- Kiểm chứng: `uv run --no-sync pytest ai -q` — 113 passed; `uv run --no-sync ruff check ai` — pass.
- P207 đã `done`. P208 và các prompt AI R2 khác vẫn tiếp tục theo bảng Tiến độ; F09/F10 chưa được nghiệm thu tích hợp.

### Hoàn tất P208 (03/10/2026)

- Bổ sung kiểm tra fact đóng lặp trong cùng delta, event đã hoàn thành không thể bị drop, và trạng thái ending không bị thay đổi bởi op hồi tưởng.
- Thêm ca đúng/sai riêng cho V09–V15: fact trùng/đóng, dependency và trạng thái event, đổi xưng hô, địa điểm, ending state, hook quá hạn, quan hệ. Hook quá hạn giữ `valid=true` và phát warning `major`.
- Kiểm chứng: `uv run --no-sync pytest ai -q` — 120 passed; `uv run --no-sync ruff check ai` — pass.
- P207 và P208 đã `done`. Checklist F09 validator vẫn để mở vì prompt P903 (fixture state dùng chung) chưa hoàn thành; F09/F10 chưa được nghiệm thu tích hợp.

### Hoàn tất P204 (03/10/2026)

- Cụm sáo theo mật độ và override được gán `minor` theo D7/D37; chính tả cảnh báo Telex/VNI chỉ khi giải mã ra âm tiết có trong seed, thêm lọc âm tiết sai có coda bất khả thi và ghi rõ giới hạn do từ điển chưa đầy đủ.
- Gộp phát hiện kiểu bỏ dấu thành finding cấp chương có số đếm/ví dụ đoạn; kiểm tra thoại giữ cảnh báo dấu câu và ngoặc không cân.
- Kiểm chứng: `uv run --no-sync pytest ai -q` — 121 passed; `uv run --no-sync ruff check ai` — pass.
- P204 đã `done`; lỗi hỏi/ngã giữa hai âm tiết hợp lệ vẫn ngoài phạm vi theo D45.

### Hoàn tất P215–P222 (03/10/2026)

- P215–P220: hoàn tất settle, validate/seam, review, sửa cục bộ có giới hạn, điều phối pipeline 11 bước và xét lại dàn ý theo mốc.
- P221: hoàn tất revise theo bốn mode, kiểm tra vùng sửa/selection, yêu cầu resettle khi nội dung đổi và chặn rework làm đổi sự kiện đã hoàn tất.
- P222: hoàn tất ba giai đoạn nền truyện, checkpoint từng phần, tiếp nối sự kiện giữa quyển, xử lý refusal/cắt output/sửa JSON một lần và tạo `StoryState` chương 0.
- Cập nhật checklist phần AI F06/F10/F11 theo các mục đã triển khai. Prompt snapshot F06 còn mở; F11 review/resettle còn mở nên chưa coi các tính năng tổng thể là verified.
- Kiểm chứng cuối: `uv run --no-sync pytest ai -q` — 135 passed; `uv run --no-sync ruff check ai` — pass.

### Hoàn tất P230 (03/10/2026)

- Thêm API đọc preset thể loại, GET/PUT danh sách cụm sáo trong `settings` với `expected_version`, chuẩn hóa văn bản, và kiểm tra văn bản trực tiếp hoặc theo chương.
- Kiểm tra dùng `LanguagePack` theo ngôn ngữ truyện; finding trả đủ `check_id`, `confidence`, `message_key`, `params`. Working copy tiếp tục được chuẩn hóa NFC qua gói ngôn ngữ.
- Thêm kiểm tra regex đầu vào và gộp cụm sáo gói/app/truyện; đăng ký route vào OpenAPI và sinh lại TypeScript contract.
- Kiểm chứng: `uv run --no-sync pytest be/tests -q` — 115 passed; test P230 sau chỉnh sửa cuối — 11 passed; `uv run --no-sync ruff check be` — pass; `uv run --no-sync python tools/contracts/check_contracts.py` — pass.
- P230 `done`. F08 tổng thể còn các API/job đánh giá model, migration `model_evals`/các cột liên quan và tích hợp findings pipeline; các việc này chưa nằm trong P230.

### R2 BE: P235–P240 (03/10/2026)

- Thêm runner write có khóa truyện, pinned model, checkpoint/progress adapter, lưu candidate từng phần và resume job interrupted từ stage đã checkpoint. Runner dùng `runtime.longform_pipeline_executor`; runtime chưa đăng ký executor mặc định nối provider với đủ 11 stage P219.
- Thêm entry gate continuity/chương trước đã commit + state applied; commit một transaction gồm revision, StateDelta/ledger/FTS, handoff, summary nếu pipeline trả về, measurement, candidate/job và events.
- Thêm continuity/metrics, plan, handoff, seam, outline proposal, candidate accept/reject, three-way conflict detail, findings list/resolve/dismiss/user-create và resync dry-run/job tuần tự.
- Revise và resync chạy qua executor port (`runtime.revise_executor`, `runtime.resync_executor`). Runtime chưa dựng mặc định các executor này từ provider/P221; outline proposal hiện đổi trạng thái proposal nhưng chưa áp toàn bộ thay đổi lên story events. Merge candidate chưa có resolution cho mọi loại insert/delete/selection.
- P239 `done`; P235–P238 và P240 còn `doing` trong bảng prompt cho tới khi nối executor mặc định và hoàn thành các nhánh merge/outline/resync còn thiếu.
- Kiểm chứng: `uv run --no-sync pytest be/tests -q` — 125 passed; `uv run --no-sync ruff check be tools` — pass; `pnpm --filter fe gen:api` và `uv run --no-sync python tools/contracts/check_contracts.py` — pass.
