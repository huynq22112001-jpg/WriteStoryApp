# F00 — Backend (Rust shell + Python bootstrap + đóng gói)

F00 có hai phía "backend": Rust trong `desktop/src-tauri` (vòng đời, data-root) và phần khởi động của Python trong `be/src/writestory_be` (bootstrap, socket, bảo vệ API). Phần DB chỉ được gọi qua hook của F02.

## Module và file

```text
desktop/src-tauri/
  tauri.conf.json          CSP, bundle.resources, webviewInstallMode, identifier
  capabilities/main.json   Quyền tối thiểu cho cửa sổ "main"
  build.rs                 tauri_build + AppManifest liệt kê command được phép
  src/main.rs              Gọi lib::run()
  src/lib.rs               Builder: single-instance (plugin đầu tiên), dialog, state, RunEvent
  src/data_root.rs         Phân giải data-root, kiểm tra ghi, marker, con trỏ, phát hiện translocation/ổ mạng
  src/instance_lock.rs     Khóa OS độc quyền trên data/.instance.lock
  src/backend.rs           Spawn, bootstrap pipe, đọc readiness, drain stderr, giám sát exit, restart, shutdown
  src/win_job.rs           (cfg windows) Job Object KILL_ON_JOB_CLOSE
  src/boot_state.rs        Máy trạng thái BootState + phát event "boot:state"
  src/commands.rs          Tauri commands cho FE (xem bảng API)
be/src/writestory_be/
  __main__.py              Entry binary: freeze_support(), gọi bootstrap.runtime.main()
  bootstrap/runtime.py     Đọc bootstrap JSON, khóa backend, tạo thư mục, bind socket, gọi F02 migrate/reconcile, chạy uvicorn
  bootstrap/protocol.py    BootstrapConfig, ReadyMessage, ProgressMessage, FatalMessage; BACKEND_PROTOCOL_VERSION
  bootstrap/lifecycle.py   stdin EOF watcher, parent-pid watchdog, shutdown coordinator
  api/security.py          Middleware Host/Origin/token, CORS
  modules/system/router.py GET /v1/health, POST /v1/system/shutdown
  modules/dev/router.py    POST /v1/dev/mock-runs (chỉ khi dev_features bật)
tools/packaging/
  backend.spec             PyInstaller onedir, console=True, name=writestory-backend
  build_backend.py         uv sync --frozen → pyinstaller → copy vào desktop/src-tauri/resources/backend/
  sign_macos_backend.sh    codesign --options runtime --timestamp từng Mach-O trong resources/backend
  assemble_portable_win.py Gom WriteStoryApp.exe + backend/ (+ WebView2 fixed runtime) thành zip portable
tools/dev/run_desktop.py   Đặt WRITESTORY_DATA_ROOT=<repo>/data rồi chạy `pnpm tauri dev`
```

## Dữ liệu và migration

F00 không tạo bảng SQLite. Các file runtime:

| File | Nội dung | Ai ghi | Ghi chú |
|---|---|---|---|
| `<data>/.writestory-data.json` | `{data_id (UUIDv7), layout_version: 1, created_at, created_by_app_version, db_initialized: bool}` | Rust tạo khi khởi tạo data-root; Python đặt `db_initialized=true` sau migration đầu | Dùng để nhận diện data-root, so với con trỏ macOS và phát hiện "DB bị mất" |
| `<data>/.instance.lock` | Khóa OS độc quyền (advisory lock), nội dung `{pid, started_at, app_version}` chỉ để chẩn đoán | Rust | Khóa tự nhả khi tiến trình chết; không dùng "file tồn tại = đang khóa" |
| `<data>/db/.backend.lock` | Khóa OS độc quyền của backend Python | Python | Chặn chạy hai backend (kể cả backend dev chạy tay) trên một DB |
| `~/Library/Application Support/WriteStoryApp/data-root.json` (macOS) | `{version: 1, data_root (tuyệt đối), data_id, chosen_at}` | Rust | Ngoại lệ duy nhất ngoài data (Plan §3.1) |
| `%APPDATA%\WriteStoryApp\data-root.json` (Windows, chỉ khi cạnh `.exe` không ghi được) | Cùng định dạng | Rust | Đề xuất mới, xem README "Rủi ro" |
| `<data>/logs/desktop.log`, `<data>/logs/backend-stderr.log` | Log Rust và stderr Python, xoay vòng theo kích thước | Rust | Không chứa token |

Thư mục con được Python tạo nếu thiếu: `db/ assets/ imports/ exports/ backups/ logs/ cache/ tmp/` (Plan §3.1). Không có migration DB.

## API

### Tauri commands (FE → Rust, qua IPC)

| Command | Request | Response | Lỗi (code) |
|---|---|---|---|
| `get_boot_state` | — | `BootState` | — |
| `pick_data_root_folder` | — | `{path: string \| null}` (hộp thoại mở bằng plugin dialog phía Rust) | — |
| `confirm_data_root` | `{path, accept_cloud_sync_warning?: bool}` | `BootState` | `DATA_ROOT_UNWRITABLE`, `DATA_ROOT_NETWORK`, `DATA_ROOT_CLOUD_SYNC`, `DATA_ROOT_LOCKED` |
| `get_backend_session` | — | `{base_url: "http://127.0.0.1:<port>", token, protocol_version}` | `BACKEND_NOT_READY` |
| `restart_backend` | — | `BootState` | `BACKEND_NOT_READY` (đang shutdown) |
| `open_logs_folder` | — | — | Chỉ mở `<data>/logs`, không nhận path từ FE |
| `quit_app` | — | — | — |

`BootState = {phase, platform, data_root?, data_id?, error?: {code, message, detail}, backend?: {base_url, protocol_version, pid}, restart_count, progress?: {stage}}` với `phase ∈ resolving_data_root | needs_data_root | translocated | data_root_error | locked_by_other_instance | starting_backend | ready | backend_crashed | startup_failed | protocol_mismatch | shutting_down`. Event `boot:state` phát mỗi khi đổi phase. Token chỉ trả qua `get_backend_session`, không nằm trong event.

### HTTP (Python, prefix `/v1`, cần `Authorization: Bearer <token>`)

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/health` | — | `{status: "ok", protocol_version, app_version, schema_version, data_id, started_at, pid}` | `UNAUTHORIZED` (401) |
| POST | `/v1/system/shutdown` | `{reason: "app_exit" \| "restart", deadline_ms?: int}` | 202 `{accepted: true, deadline_ms}` | `UNAUTHORIZED` |
| POST | `/v1/dev/mock-runs` | `{works: int (1–5), tokens_per_sec, latency_ms, duration_s, commit_to_spike_db: bool}` | 202 `{run_ids: [...]}` | 404 khi `dev_features` tắt; `VALIDATION` |

Hợp đồng lỗi chung theo F01. Middleware bảo vệ áp cho mọi route trừ preflight CORS.

## Logic xử lý

### A. Phân giải data-root (Rust `data_root.rs`, Plan §3, §3.1, FL01)

1. Build debug: nếu có env `WRITESTORY_DATA_ROOT` thì dùng (dev root `E:/pm/WriteStoryApp/data`, Arch §10); release bỏ qua env này.
2. Windows: `exe_dir/data`. Nếu ghi được → dùng. Nếu không: đọc `%APPDATA%\WriteStoryApp\data-root.json`; không có → `phase=needs_data_root` kèm `error.code=DATA_ROOT_UNWRITABLE` để FE cho chọn thư mục. Không tự chọn AppData.
3. macOS: đọc con trỏ `data-root.json`. Có và thư mục tồn tại → dùng; marker `data_id` khác con trỏ → `data_root_error` (`DATA_ROOT_MISMATCH`), cho chọn lại. Không có con trỏ:
   - Đường dẫn `current_exe()` chứa `/AppTranslocation/` → `phase=translocated` (hướng dẫn kéo vào Applications, nút Thoát).
   - Ngược lại → `phase=needs_data_root`, gợi ý `<thư mục chứa .app>/data` nếu ghi được, nếu không `~/Library/Application Support/WriteStoryApp/data`.
4. Kiểm tra thư mục được chọn: tuyệt đối, tạo được; ghi thử `tmp/.write-test-<rand>` (write + fsync + rename + xóa), có đường dẫn Unicode/khoảng trắng; từ chối ổ mạng (Windows `GetDriveTypeW == DRIVE_REMOTE` hoặc UNC `\\`; macOS `statfs` không có `MNT_LOCAL`) → `DATA_ROOT_NETWORK`; cảnh báo thư mục đồng bộ đám mây (đường dẫn chứa `Library/Mobile Documents`, `Library/CloudStorage`, hoặc nằm dưới `%OneDrive%`) → `DATA_ROOT_CLOUD_SYNC`, chỉ cho tiếp khi FE gửi `accept_cloud_sync_warning=true` (Plan §3.1: không dùng data đang hoạt động trên thư mục cloud sync). Phát hiện cloud sync là heuristic, ghi rõ trong UI.
5. Thư mục rỗng → tạo marker `.writestory-data.json`. Thư mục có marker → dùng `data_id` của nó. Thư mục không rỗng, không có marker → `DATA_ROOT_NOT_EMPTY`, yêu cầu chọn thư mục rỗng hoặc data-root cũ.
6. Lấy khóa `.instance.lock` (crate `fs4`, `try_lock_exclusive`). Thất bại → `phase=locked_by_other_instance` (`DATA_ROOT_LOCKED`).
7. macOS/Windows-pointer: ghi con trỏ bằng file tạm + rename.

Single-instance: `tauri-plugin-single-instance` đăng ký **trước** mọi plugin; lần mở thứ hai gọi callback → `show + unminimize + set_focus` cửa sổ main rồi tiến trình mới thoát. Khóa data-root là lớp thứ hai cho trường hợp hai bản app khác nhau.

### B. Spawn và readiness (Rust `backend.rs`, Python `bootstrap/runtime.py`)

1. Rust sinh token 32 byte ngẫu nhiên (`getrandom`), mã hóa base64url; giữ trong `BackendState` (Mutex), không log.
2. Đường dẫn binary: `app.path().resource_dir()/backend/writestory-backend[.exe]`; kiểm tra tồn tại và (macOS) bit thực thi. Spawn bằng `std::process::Command` với `stdin/stdout/stderr = piped`, `current_dir = data_root` (Python vẫn không suy ra gì từ cwd), Windows `creation_flags(CREATE_NO_WINDOW)` (binary build `console=True` để stdio hoạt động, không hiện cửa sổ).
3. Windows: ngay sau spawn gán tiến trình vào Job Object có `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`; handle job giữ tới khi app thoát (đóng handle = kill cả cây).
4. Rust ghi một dòng JSON vào stdin rồi **giữ stdin mở**: `{"protocol_version":1,"token":"…","data_root":"<abs>","data_id":"…","parent_pid":1234,"app_version":"…","allowed_origins":["tauri://localhost","http://tauri.localhost"],"dev_features":false,"log_level":"info"}`.
5. Python `__main__`: `multiprocessing.freeze_support()`; nhân bản fd 1 làm kênh protocol, đặt `sys.stdout = sys.stderr` để thư viện in lung tung không làm hỏng protocol. Đọc đúng một dòng stdin (timeout 10 giây) → `BootstrapConfig` (Pydantic). `protocol_version` khác → in `fatal PROTOCOL_MISMATCH`, exit 3.
6. Python lấy `db/.backend.lock`; thất bại → `fatal DATA_ROOT_LOCKED`. Tạo thư mục con; cấu hình logging xoay vòng `logs/backend.log` với bộ lọc che token/API key.
7. `sock = socket.socket(AF_INET); sock.bind(("127.0.0.1", 0)); sock.listen(); port = sock.getsockname()[1]` — OS cấp cổng, giữ socket để trao cho uvicorn (Review §7.2).
8. Gọi hook F02 `prepare_database(config, progress_cb)` (backup trước migrate, migrate, reconcile). Trong lúc chạy, in `{"event":"progress","stage":"migrating"|"reconciling"}`; lỗi → `{"event":"fatal","code":"MIGRATION_FAILED"|"SCHEMA_TOO_NEW"|"DB_MISSING","message":"…","detail":{…}}` rồi exit 4.
9. `app = create_app(runtime)`; `server = uvicorn.Server(uvicorn.Config(app, lifespan="on", log_config=None, timeout_graceful_shutdown=<giây>))`; task chờ `server.started` rồi in `{"event":"ready","port":p,"protocol_version":1,"pid":…}`; `await server.serve(sockets=[sock])`.
10. Rust đọc stdout theo dòng: `progress` → cập nhật `BootState.progress` và **gia hạn** timeout; `ready` → gọi `GET /v1/health` với token (timeout 2 giây, thử lại 3 lần), khớp `protocol_version` và `data_id` → `phase=ready`; `fatal` → `startup_failed` kèm code. Timeout readiness mặc định 60 giây không có dòng mới (giả định, chỉnh sau đo R0).
11. Rust drain stderr liên tục sang `logs/backend-stderr.log` và ring buffer 200 dòng (tránh đầy pipe làm treo Python); ring buffer gửi kèm lỗi crash cho FE.

### C. Bảo vệ API (Python `api/security.py`, Plan §3)

1. Thứ tự middleware: CORS (ngoài cùng) → `LocalSecurityMiddleware` → router.
2. `Host` phải đúng `127.0.0.1:<port>`; sai → 400 `FORBIDDEN_HOST` (chống DNS rebinding).
3. `Origin` (nếu có) phải thuộc `allowed_origins` từ bootstrap (thêm `http://localhost:5173` chỉ khi `dev_features`); `Origin: null` hoặc lạ → 403 `FORBIDDEN_ORIGIN`. Không có `Origin` (Rust health check) vẫn phải có token.
4. Preflight `OPTIONS` từ origin hợp lệ được CORS trả 204 mà không cần token; CORS `allow_headers = Authorization, Content-Type, Idempotency-Key, Last-Event-ID`, `expose_headers = Retry-After, X-Request-Id`, không `allow_credentials`.
5. Token so bằng `hmac.compare_digest`; thiếu/sai → 401 `UNAUTHORIZED`. Không có route nào nhận token qua query string.

CSP trong `tauri.conf.json` (đối chiếu khi dựng): `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; worker-src 'self' blob:; connect-src 'self' ipc: http://ipc.localhost http://127.0.0.1:*`. Capability `main.json`: `core:default` + các command ở bảng trên; **không** cấp `shell:*`, `fs:*`, `dialog:*` cho FE (hộp thoại mở từ Rust).

### D. Shutdown (Plan §3 bước 7, Review §7.1)

1. `RunEvent::ExitRequested` (lần đầu): `api.prevent_exit()`, `phase=shutting_down`, gọi `POST /v1/system/shutdown {reason:"app_exit", deadline_ms: 5000}` (giả định), chờ child thoát tối đa `deadline + 2 giây`; quá hạn → `child.kill()`; rồi `app.exit(0)`.
2. `RunEvent::Exit` (macOS có thể tới thẳng đây): nếu child còn sống → gọi shutdown đồng bộ timeout ngắn (1 giây), đóng stdin, chờ 2 giây, kill.
3. Python nhận shutdown: ngừng nhận request mới (503 `BACKEND_SHUTTING_DOWN`), báo supervisor (F12) checkpoint + đánh dấu job đang chạy `interrupted`, flush writer queue và `PRAGMA optimize`/checkpoint WAL (F02), nhả khóa, `server.should_exit = True`.
4. Lưới an toàn: (a) Windows Job Object kill cả cây khi Rust chết; (b) Python theo dõi stdin: `readline()` trả EOF (Rust chết/đóng pipe) → shutdown với deadline 3 giây rồi `os._exit(0)`; (c) watchdog kiểm tra `parent_pid` mỗi 2 giây (giả định) cho trường hợp pipe bị kế thừa.
5. Restart (`restart_backend`): shutdown như trên với `reason:"restart"`, spawn lại (token mới, cổng mới), `restart_count += 1`.

### E. Giám sát crash

Thread chờ `child.wait()`: nếu thoát khi `phase=ready` và không có yêu cầu shutdown → `phase=backend_crashed`, `error = {code: "BACKEND_EXITED", detail: {exit_code, stderr_tail}}`. Không tự khởi động lại trong MVP (người dùng bấm nút); ghi vào `desktop.log`.

### F. Đóng gói và spike R0 (Plan §9 G0, §10; Review §7.1)

1. `build_backend.py`: cài BE + AI vào môi trường build (`uv sync --frozen`), PyInstaller onedir với `backend.spec`: `collect_data_files("writestory_ai")` (prompts/methods/manifest), thêm `be/migrations` + `alembic.ini` làm data, hidden imports cho provider registry và `aiosqlite`. Kiểm `importlib.resources` đọc được trong bản frozen.
2. `tauri.conf.json`: `bundle.resources` dạng thư mục `"resources/backend/"` (đệ quy, giữ cấu trúc; không dùng `"dir/**"`, Review §7.1); đích trên máy là `<resource_dir>/backend/`. Mapping thực tế ghi vào ADR.
3. Windows: `bundle.windows.webviewInstallMode` thử `offlineInstaller` (installer) và `fixedRuntime` (portable zip); xác nhận tên khóa trong schema.
4. macOS: `sign_macos_backend.sh` ký từng `.dylib/.so`/binary trong `resources/backend` bằng cùng Developer ID, `--options runtime --timestamp` **trước** `tauri build`; DMG có symlink `/Applications`. Chốt macOS tối thiểu.
5. Build trên đúng OS (không cross-compile PyInstaller).

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `boot:state` (Tauri event, không phải SSE) | Mỗi lần đổi phase | `BootState` |
| `backend.notice` (SSE, F01) | Sau khi ready nếu reconcile có job bị gián đoạn; trước shutdown | `{kind: "shutting_down" \| "jobs_interrupted", detail}` |
| `token.delta` / `job.step` (SSE, chỉ `mock-runs`) | Spike stream | Theo envelope F01 |

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Thư mục cạnh `.exe` không ghi được | `needs_data_root` + giải thích, không tự dùng AppData | `DATA_ROOT_UNWRITABLE` |
| Data-root trên ổ mạng | Từ chối | `DATA_ROOT_NETWORK` |
| Data-root trong thư mục cloud sync | Cảnh báo, cần xác nhận | `DATA_ROOT_CLOUD_SYNC` |
| Con trỏ macOS trỏ tới thư mục đã mất (ổ ngoài rút ra) | `data_root_error`, cho chọn lại hoặc thử lại; không tạo data mới tự động | `DATA_ROOT_MISSING` |
| `data_id` marker khác con trỏ | `data_root_error`, hỏi dùng thư mục này hay chọn lại | `DATA_ROOT_MISMATCH` |
| Marker `db_initialized=true` nhưng `db/app.sqlite3` không có | Python `fatal DB_MISSING`; FE cho khôi phục backup (F13) hoặc tạo DB mới có xác nhận (FL01) | `DB_MISSING` |
| Bản app khác đang giữ data-root | `locked_by_other_instance` | `DATA_ROOT_LOCKED` |
| Binary backend thiếu/không có quyền thực thi | `startup_failed` | `BACKEND_BINARY_MISSING` |
| Không có dòng readiness trong thời hạn | Kill child, `startup_failed` + stderr tail | `BACKEND_START_TIMEOUT` |
| Protocol version khác | `protocol_mismatch` (bản cài hỏng/lẫn phiên bản) | `PROTOCOL_MISMATCH` |
| DB schema mới hơn app | Không mở, không migrate | `SCHEMA_TOO_NEW` |
| Migration lỗi | Giữ DB ở revision cuối thành công + đường dẫn backup | `MIGRATION_FAILED` |
| Backend crash khi đang chạy | `backend_crashed`, nút khởi động lại | `BACKEND_EXITED` |
| Gọi API khi đang shutdown | 503, `retryable=false` | `BACKEND_SHUTTING_DOWN` |

## Việc cần làm

- [x] Scaffold `desktop/` (pnpm workspace member), `tauri.conf.json` trỏ `frontendDist: ../../fe/dist`, `devUrl` Vite.
- [x] `data_root.rs`: phân giải data-root Windows/macOS, kiểm tra ghi, marker/con trỏ, cloud sync, ổ mạng, translocation; unit test writable/unwritable, mismatch, translocation, UNC và cloud sync.
- [x] Plugin single-instance Tauri đăng ký đầu tiên; `instance_lock.rs` khóa độc quyền bằng fs4.
- [x] `backend.rs`: spawn dev, bootstrap JSON, đọc stdout NDJSON, drain stderr, health check, giám sát exit.
- [x] `backend.rs`: restart backend khi có command (P012).
- [x] `win_job.rs` (crate `windows`): Job Object `KILL_ON_JOB_CLOSE`.
- [ ] `win_job.rs`: kiểm thử kill-on-close khi thoát app (smoke đóng gói).
- [x] Xử lý `ExitRequested` + `Exit`; thử đóng cửa sổ và kill app trên Windows.
- [ ] Thử Cmd+Q trên macOS và kill-on-close trên bản đóng gói.
- [ ] Python `__main__.py`, `bootstrap/protocol.py`, `bootstrap/runtime.py`, `bootstrap/lifecycle.py` (stdin EOF, parent watchdog).
- [ ] `api/security.py` + CORS; `modules/system/router.py` (`/v1/health`, `/v1/system/shutdown`).
- [ ] `modules/dev/router.py` `mock-runs` chỉ đăng ký khi `dev_features=true`; kiểm bản release không có route.
- [ ] `tools/packaging/*` cho Windows x64 và macOS arm64; CI job theo OS.
- [ ] Spike R0: chạy checklist Plan §9 G0 trên máy sạch; đo startup lạnh, RAM idle, dung lượng bundle; ghi ADR (Tauri vs Electron, sidecar vs resources, WebView2 mode, macOS tối thiểu).
- [x] R0 Windows x64: PyInstaller onedir, Tauri resource spawn, NSIS `offlineInstaller` artifact build và direct release smoke tới `ready`; số đo nằm trong ADR-002.
- [ ] Cài thử NSIS trên máy sạch không có Python/uv; xác nhận WebView2 offline installer và portable/fixedRuntime.
- [x] Chuẩn bị script ký Mach-O và hướng dẫn DMG trong ADR-003; chưa chạy trên macOS.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit (Rust) | Phân giải data-root: writable/unwritable, translocated, con trỏ hỏng, mismatch, ổ mạng, cloud sync | `desktop/src-tauri/src/data_root.rs` (`#[cfg(test)]`) |
| unit (Rust) | Parse NDJSON stdout: ready/progress/fatal, dòng rác bị bỏ qua | `desktop/src-tauri/src/backend.rs` (`#[cfg(test)]`) |
| unit | `BootstrapConfig` validate, protocol mismatch → exit code 3 | `be/tests/unit/bootstrap/test_protocol.py` |
| unit | Middleware: thiếu token 401, Host sai 400, Origin lạ 403, preflight 204, token không bị log | `be/tests/unit/api/test_security.py` |
| integration | Chạy `python -m writestory_be` với data-root tạm qua stdin: nhận `ready`, `/v1/health` đúng `data_id`; đóng stdin → tiến trình thoát trong deadline | `be/tests/integration/test_bootstrap_process.py` |
| integration | Hai backend cùng data-root → backend thứ hai `fatal DATA_ROOT_LOCKED` | `be/tests/integration/test_backend_lock.py` |
| desktop | Smoke trên bản đóng gói: mở, health, đóng, không còn tiến trình; kill Tauri (Windows) → backend chết theo Job Object | `tests/desktop/smoke_lifecycle.py` |
| thủ công | macOS translocation (mở từ Downloads), chọn data-root, Unicode path `D:\Truyện của tôi\` | Checklist trong [T01](../../tests/flows/T01-khoi-dong-va-data-root.md) |

## Tên mới đề xuất

- File runtime: `<data>/.writestory-data.json` (marker, trường `data_id`, `layout_version`, `db_initialized`), `<data>/.instance.lock`, `<data>/db/.backend.lock`, `<data>/logs/desktop.log`, `<data>/logs/backend-stderr.log`, `%APPDATA%\WriteStoryApp\data-root.json` (Windows, chỉ khi cạnh exe không ghi được).
- Rust: `instance_lock.rs`, `win_job.rs`, `boot_state.rs`, `commands.rs`; commands `get_boot_state`, `pick_data_root_folder`, `confirm_data_root`, `get_backend_session`, `restart_backend`, `open_logs_folder`, `quit_app`; event `boot:state`; kiểu `BootState` và các phase liệt kê ở trên.
- Python: `bootstrap/protocol.py` (`BootstrapConfig`, `BACKEND_PROTOCOL_VERSION`), `bootstrap/runtime.py`, `bootstrap/lifecycle.py`, `api/security.py` (`LocalSecurityMiddleware`), `modules/system/`, `modules/dev/`; hook F02 `prepare_database`.
- API: `POST /v1/system/shutdown`, `POST /v1/dev/mock-runs` (chỉ dev). Trường response `/v1/health`.
- Env dev: `WRITESTORY_DATA_ROOT` (chỉ build debug).
- Mã lỗi khởi động (không thuộc HTTP API chung): `DATA_ROOT_UNWRITABLE`, `DATA_ROOT_NETWORK`, `DATA_ROOT_CLOUD_SYNC`, `DATA_ROOT_MISSING`, `DATA_ROOT_MISMATCH`, `DATA_ROOT_NOT_EMPTY`, `DATA_ROOT_LOCKED`, `DB_MISSING`, `BACKEND_BINARY_MISSING`, `BACKEND_START_TIMEOUT`, `PROTOCOL_MISMATCH`, `SCHEMA_TOO_NEW`, `MIGRATION_FAILED`, `BACKEND_EXITED`, `BACKEND_NOT_READY`. Mã HTTP: `UNAUTHORIZED`, `FORBIDDEN_HOST`, `FORBIDDEN_ORIGIN`, `BACKEND_SHUTTING_DOWN` (đăng ký trong bảng mã của F01).
- Tools: `tools/packaging/backend.spec`, `build_backend.py`, `sign_macos_backend.sh`, `assemble_portable_win.py`, `tools/dev/run_desktop.py`. Tên binary `writestory-backend`.
