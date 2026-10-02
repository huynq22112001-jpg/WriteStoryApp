# T01 — Khởi động, data-root, single-instance, tắt app

Tính năng: F00. Nguồn: Plan FL01, §3, §3.1, §4.1 (frozen process pool), §10, §11 (Desktop, Packaging), §9 Giai đoạn 0. Cấp test chính: desktop, integration.

## Mục đích

Chứng minh app mở được trên máy sạch Windows/macOS với đúng một data-root tuyệt đối, đúng một backend, cổng động không xung đột, không bao giờ tạo DB ở vị trí khác khi có lỗi, và đóng app (kể cả bị kill) không để lại tiến trình backend mồ côi.

## Tiền điều kiện và dữ liệu

- Bản portable Windows x64 và `.app`/`.dmg` macOS arm64 đã build bằng PyInstaller onedir; VM sạch không có Python/Node.
- Data-root tạm cho integration: `tmp_path/"Truyện của tôi"/data` (có dấu và khoảng trắng).
- Fixture DB cũ: `tests/fixtures/db/app_schema_v1.sqlite3` (schema cũ hơn head, có 2 truyện, 12 chương) để test migration.
- Backend chạy trực tiếp cho integration: `python -m writestory_be` nhận bootstrap JSON qua stdin.
- Mock provider: `{latency_ms: 20, tokens_per_sec: 400, scripted_outputs: {write: "tien_hiep_01/ch04.txt"}}` (chỉ dùng ở T01-12 để có job đang chạy khi tắt).

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T01-01 | thành công | 1. Giải nén portable vào `E:\WSA test\` chưa có `data/`. 2. Chạy `WriteStoryApp.exe`. 3. Chờ màn "đang khởi động" chuyển sang onboarding. | Tạo đủ `data/db`, `assets`, `imports`, `exports`, `backups`, `logs`, `cache`, `tmp`; `data/db/app.sqlite3` có `journal_mode=wal`, `foreign_keys=1`, `synchronous=2` (FULL), Alembic ở head. Không có cửa sổ console. Cây tiến trình: 1 shell + 1 backend. Thời gian tới readiness được ghi lại (mục tiêu < 5 s). `GET /v1/health` 200, `protocol_version` khớp shell. | desktop | `tests/desktop/smoke_startup_windows.ps1` |
| T01-02 | thành công | 1. Spawn backend, ghi bootstrap `{data_root, token, protocol_version}` vào stdin. 2. Đọc dòng readiness trên stdout. | Readiness có `port`, `protocol_version`; socket bind `127.0.0.1` với cổng do OS cấp (yêu cầu cổng 0); fd socket báo readiness chính là fd truyền vào `Server.serve(sockets=[...])` (không đóng rồi bind lại). Backend không đọc data-root từ working directory (chạy với `cwd` khác vẫn dùng đúng `data_root`). | integration | `be/tests/integration/test_bootstrap_readiness.py` |
| T01-03 | bảo mật | Gọi `GET /v1/works`: (a) không có `Authorization`; (b) token sai; (c) `Host: evil.example`; (d) `Origin: http://evil.example`; (e) đúng token + origin Tauri. | (a)(b) 401; (c)(d) 403; (e) 200. Token xuất hiện 0 lần trong `data/logs/**` và trong mọi URL request (kiểm bằng log truy cập). Không có route nào bind ngoài loopback. | integration | `be/tests/integration/test_local_auth.py` |
| T01-04 | lỗi | 1. Windows: đặt portable vào `C:\Program Files\WriteStoryApp\`, chạy bằng user thường. 2. Integration: data-root có ACL chỉ đọc. | Rust phát hiện trước khi spawn backend; hộp thoại lỗi có đường dẫn cụ thể và nút "Chọn thư mục data khác". Không có `app.sqlite3` nào được tạo ở `%APPDATA%`, `%LOCALAPPDATA%`, `%TEMP%` hay cạnh app (quét = 0 file). Không hiển thị thư viện trống. Không chạy app bằng administrator. | desktop | `tests/desktop/test_unwritable_data_root.ps1` |
| T01-05 | biên | Khi app đang chạy, mở lần hai. | Tiến trình thứ hai thoát trong ≤ 2 s, cửa sổ đầu được focus. Vẫn chỉ 1 backend; file khóa data-root không đổi chủ. | desktop | `tests/desktop/test_single_instance.ps1`, `tests/desktop/test_single_instance.sh` |
| T01-06 | lỗi | Hai bản portable khác thư mục cùng trỏ một data-root (macOS: hai bản app cùng `data-root.json`); mở bản thứ hai khi bản đầu đang chạy. | Bản thứ hai báo "data-root đang được tiến trình khác dùng" kèm PID; không migrate, không reconcile job, không spawn worker. Bản đầu không bị ảnh hưởng. | desktop | `tests/desktop/test_data_root_lock.py` |
| T01-07 | phục hồi | 1. Kill cứng cả shell và backend (`taskkill /F /T`). 2. Mở lại. | Khóa data-root cũ (PID đã chết) được thu hồi tự động; app khởi động bình thường; `PRAGMA integrity_check` = `ok`. | desktop | `tests/desktop/test_stale_lock_reclaim.py` |
| T01-08 | lỗi | 1. Chiếm 200 cổng ngẫu nhiên vùng ephemeral bằng listener giả. 2. Khởi động backend 20 lần liên tiếp. 3. Ngay sau readiness, tiến trình khác thử bind cùng cổng. | 20/20 lần khởi động thành công, 0 lỗi `EADDRINUSE`; cổng trong readiness luôn khác cổng bị chiếm; tiến trình khác bind cổng đó thất bại (cổng đã được giữ, không có khe TOCTOU). | integration | `be/tests/integration/test_port_conflict.py` |
| T01-09 | lỗi | Shell mong `protocol_version=1`, stub backend trả `2`. | Shell hiển thị lỗi phiên bản giao thức cụ thể, terminate backend, không nạp FE vào backend đó. | integration | `tests/desktop/test_protocol_mismatch.py` |
| T01-10 | phục hồi | 1. Copy `app_schema_v1.sqlite3` vào data-root. 2. Khởi động (migration bình thường). 3. Lặp lại với một migration bị tiêm lỗi (`WS_TEST_FAULT=migration:fail`). | Bước 2: trước migrate có backup tại `data/backups/pre-migrate-<ts>/`; sau migrate vẫn 2 truyện, 12 chương, nội dung trùng checksum. Bước 3: DB giữ nguyên version cũ, màn lỗi ghi rõ migration thất bại và vị trí backup; không tạo DB mới, không hiển thị thư viện trống. | integration | `be/tests/integration/test_startup_migration.py` |
| T01-11 | phục hồi | DB có 2 `jobs` ở `running` và 1 `work_locks` hết lease từ lần chạy trước; khởi động. | Cả 2 job chuyển `interrupted`, phát `job.state` tương ứng; khóa hết lease được giải phóng; job `queued` giữ nguyên. Chi tiết resume ở T09. | integration | `be/tests/integration/test_startup_reconcile.py` |
| T01-12 | thành công | 1. Có 1 job write đang ở bước `write` (mock chậm). 2. Đóng cửa sổ. | Shell gọi endpoint shutdown; backend lưu checkpoint bước hiện tại vào `job_steps`, thoát trong ≤ 10 s, mã thoát 0. Sau 15 s không còn tiến trình backend. Lần mở sau job ở `interrupted`, có nút Resume. | desktop | `tests/desktop/test_graceful_shutdown.py` |
| T01-13 | phục hồi | Windows: `taskkill /F /PID <shell>` (không graceful) khi backend đang chạy job. | Backend chết trong ≤ 2 s nhờ Job Object kill-on-close; `Get-Process` không còn backend; lần mở sau `integrity_check` = `ok`, job `interrupted`. Lặp 20 lần: 0 tiến trình mồ côi. | desktop | `tests/desktop/test_job_object_kill.ps1` |
| T01-14 | phục hồi | (a) macOS: `kill -9 <shell>`. (b) Integration: test harness đóng stdin của backend. | Backend phát hiện EOF trên stdin, chạy shutdown có checkpoint và thoát trong ≤ 5 s; `pgrep -f writestory` rỗng. Lặp 20 lần: 0 mồ côi. | desktop, integration | `tests/desktop/macos_orphan_check.sh`, `be/tests/integration/test_stdin_eof_shutdown.py` |
| T01-15 | biên | macOS: thoát bằng Cmd+Q và bằng menu Dock "Quit" (trường hợp không phát `ExitRequested`). | Handler `RunEvent::Exit` vẫn gọi shutdown; backend thoát, không mồ côi. | desktop | `tests/desktop/macos_quit_paths.sh` |
| T01-16 | lỗi | Tiêm `WS_TEST_FAULT=shutdown:hang` để endpoint shutdown treo. | Sau deadline (10 s) shell terminate tiến trình con; không còn backend; lần mở sau job `interrupted`. | integration | `tests/desktop/test_shutdown_deadline.py` |
| T01-17 | biên | macOS: tải zip, giữ cờ `com.apple.quarantine`, mở app từ `~/Downloads`. Sau đó kéo vào `/Applications` bằng Finder và mở lại. | Lần 1: phát hiện `/AppTranslocation/` trong đường dẫn executable, hiện hướng dẫn kéo vào Applications; không ghi `data-root.json`, không tạo `data/` ở đâu. Lần 2: hiện bước chọn data-root, gợi ý `data` cạnh `.app` nếu ghi được, ngược lại `~/Library/Application Support/WriteStoryApp/data`; chọn xong ghi `~/Library/Application Support/WriteStoryApp/data-root.json` chỉ gồm đường dẫn tuyệt đối + ID data. Lần 3 mở không hỏi lại. | thủ công, desktop | `tests/desktop/macos_translocation.md` (checklist) |
| T01-18 | lỗi | macOS: `data-root.json` trỏ tới ổ ngoài đã rút. | Lỗi nêu đường dẫn, nút "Thử lại"/"Chọn lại"; không tạo DB rỗng ở đường dẫn cũ hay đường dẫn mặc định. | desktop | `tests/desktop/macos_missing_data_root.sh` |
| T01-19 | biên | Data-root `D:\Truyện của tôi\WSA\data` và `~/Tài liệu/Truyện/data`; thêm 1 asset. | Khởi động bình thường; `assets` lưu đường dẫn tương đối (không bắt đầu bằng ký tự ổ đĩa hoặc `/`). Copy cả thư mục sang máy khác (app đã đóng) vẫn mở được. | desktop | `tests/desktop/test_unicode_data_root.py` |
| T01-20 | biên | Bản frozen: kích hoạt tác vụ test dùng `ProcessPoolExecutor` (spawn). | Không sinh backend thứ hai, không có readiness/bind cổng thứ hai, không khởi động lại migration; `freeze_support` hoạt động. | desktop | `tests/desktop/test_frozen_process_pool.py` |
| T01-21 | thành công | VM Windows/macOS sạch (không Python/Node): mở app, tạo truyện, chạy 1 job mock stream, đóng app. | App chạy không cần runtime ngoài; stream hiển thị; sau khi đóng không còn backend trong Task Manager/Activity Monitor. | thủ công | `tests/desktop/clean_machine_checklist.md` |

## Kiểm tra dữ liệu sau test

- DB: chỉ một `data/db/app.sqlite3` trong data-root; `PRAGMA integrity_check` = `ok`; Alembic version = head (trừ T01-10 bước 3 giữ version cũ).
- Job: không còn job `running` sau khởi động lại; job đang chạy lúc tắt/kill ở `interrupted` với checkpoint bước cuối hợp lệ.
- Event: `job.state` cho các job được reconcile; `backend.notice` khi thu hồi khóa cũ.
- File: không có file `app.sqlite3` hay `data/` ngoài data-root đã chọn; trên macOS ngoài data-root chỉ có `data-root.json`.
- Log: token phiên và API key xuất hiện 0 lần trong `data/logs/**`.

## Tiêu chí pass

- 0 tiến trình backend mồ côi qua 20 chu kỳ đóng bình thường + 20 chu kỳ kill trên mỗi OS.
- 0 DB/thư mục data tạo ngoài data-root trong mọi kịch bản lỗi (T01-04, T01-06, T01-17, T01-18).
- 20/20 lần khởi động không lỗi cổng khi có 200 cổng bị chiếm.
- Khởi động lạnh tới readiness: ghi p50/p95 cho mỗi OS; mục tiêu < 5 s trên máy tham chiếu (tiêu chí đề xuất, chỉnh sau đo R0).
- Mọi lỗi khởi động hiển thị nguyên nhân + đường dẫn/PID/cổng cụ thể và hành động gợi ý.

## Ghi chú thủ công

- T01-17 phải chạy trên máy macOS thật, file tải qua trình duyệt (để có quarantine), cả từ zip và từ DMG chưa kéo vào Applications.
- T01-21: dùng VM có snapshot sạch để chạy lại sau mỗi bản build; ghi phiên bản OS, WebView2/WKWebView.
- Đo thời gian khởi động lạnh sau khi khởi động lại máy (cache OS nguội), ghi vào báo cáo R0.

## Tên mới đề xuất

- `POST /v1/system/shutdown`: endpoint shutdown mà §3 bước 7 nhắc nhưng chưa đặt tên.
- Bootstrap payload `{data_root, token, protocol_version, parent_pid}`; dòng readiness `{port, protocol_version, pid}`.
- Khóa data-root: `data/.lock` (PID + thời điểm); ID data: `settings.data_id`, cũng ghi trong `data-root.json` dạng `{path, data_id}`.
- Thư mục backup trước migrate: `data/backups/pre-migrate-<ts>/`.
- Mã lỗi khởi động (shell hiển thị, ngoài §23.1.D): `DATA_ROOT_UNWRITABLE`, `DATA_ROOT_LOCKED`, `DATA_ROOT_MISSING`, `APP_TRANSLOCATED`, `PROTOCOL_MISMATCH`, `MIGRATION_FAILED`.
- Biến môi trường chỉ dùng trong test: `WS_TEST_FAULT=<điểm>:<hành vi>` để tiêm lỗi.
