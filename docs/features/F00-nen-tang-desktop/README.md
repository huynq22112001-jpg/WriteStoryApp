# F00 — Nền tảng desktop: Tauri shell, vòng đời backend, data-root, đóng gói

Giai đoạn: R0 (spike tuần 1), hoàn thiện phần single-instance/data-root ở R1. Trạng thái: planned.

## Mục tiêu

Người dùng mở một app desktop duy nhất (Windows x64, macOS arm64) trên máy sạch không có Python/Node: app tự xác định thư mục `data`, khởi động backend Python đóng gói, kết nối an toàn qua loopback và tắt sạch khi thoát, không để lại tiến trình mồ côi. Khi backend đang khởi động, bị crash hoặc mất kết nối, giao diện báo rõ và cho khởi động lại.

## Phạm vi

- Trong phạm vi:
  - Rust/Tauri: single-instance, phân giải data-root (Windows cạnh `.exe`; macOS con trỏ `data-root.json` + phát hiện App Translocation + bước chọn thư mục), kiểm tra quyền ghi, khóa data-root.
  - Vòng đời backend: spawn binary PyInstaller onedir từ `bundle.resources`, bootstrap qua stdin pipe (token, data-root), readiness qua stdout, cổng loopback động với socket bind sẵn, shutdown endpoint, `RunEvent::ExitRequested` + `RunEvent::Exit`, Windows Job Object, theo dõi EOF stdin.
  - Bảo vệ API local: token Bearer, kiểm tra `Host`/`Origin`, CORS, CSP, Tauri capabilities tối thiểu.
  - Spike đóng gói: PyInstaller onedir, WebView2 `offlineInstaller`/`fixedRuntime`, ký từng file trên macOS, checklist R0 (Plan §9 Giai đoạn 0).
  - FE: cầu nối bootstrap (`shared/desktop/bridge.ts`), các màn trạng thái backend: đang khởi động, chọn data-root, lỗi khởi động, backend dừng bất ngờ, banner mất kết nối.
  - Endpoint dev `mock-runs` cho spike stream 3 truyện song song (chỉ bật ở chế độ dev).
- Ngoài phạm vi:
  - Envelope sự kiện, hợp đồng lỗi, event bus FE → F01.
  - SQLite pragma, migration, writer queue → F02 (F00 chỉ gọi bước "migrate + reconcile" ở bootstrap).
  - Onboarding, vault → F03. Spike editor/IME tiếng Việt → F07 (cùng tuần R0 nhưng tách tính năng).
  - Giữ máy thức, thông báo native → F14. Installer có ký + auto-update → R7 (Plan §10, NEW08).

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| — | Tính năng nền đầu tiên. F01 (khung event bus) làm song song trong R0 để chạy spike stream |

## Nguồn thiết kế

- Plan §1 (data gom một chỗ), §2 (stack: Tauri 2, CPython 3.14, PyInstaller onedir), §3 (vòng đời mở/đóng app 7 bước), §3.1 (data-root, App Translocation), §4.1 (`freeze_support`), §9 Giai đoạn 0, §10 (đóng gói), §11 (test Desktop/Packaging), FL01, §21 dòng "Full Win/Mac release", §23.4 #2.
- Arch §3 (`desktop/src-tauri/src/backend.rs`, `data_root.rs`), §4 (`shared/desktop/bridge.ts`), §7 (đóng gói BE+AI), §10 (data-root, dev root `E:/pm/WriteStoryApp/data`).
- UI §4 (status bar "backend ✓"), §5.8 (trạng thái backend), §10 (kiểm chứng R0).
- Review §1 #5, #13; §7 (App Translocation), §7.1 (sidecar target-triple, `bundle.resources` `"dir/"`, onefile vs onedir, codesign, WebView2, tauri#14360, CPython 3.14), §7.2 (uvicorn `Server.serve(sockets=[...])`).
- Mã feature Plan: NEW01 (§19), OPS12 (health/runtime check, §15.15).

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Rust shell (data-root, lock, spawn, readiness, shutdown, Job Object) + Python bootstrap (`__main__`, socket, readiness, stdin watcher, health/shutdown, middleware Host/Origin/token) + đóng gói |
| FE | [fe.md](./fe.md) | `bridge.ts`, `BootGate`, màn khởi động/chọn data-root/translocation/lỗi/crash, banner mất kết nối |
| AI | [ai.md](./ai.md) | Chỉ mock provider cho spike stream; không có workflow AI |

## Tiêu chí hoàn thành

- [ ] Máy sạch Windows x64 và macOS arm64 (không cài Python/Node) mở được app; status bar hiện "backend ✓" (Plan §9 G0).
- [ ] Mở lần hai cùng bản cài → focus cửa sổ cũ, không spawn backend thứ hai; hai bản app khác nhau trỏ cùng data-root → bản sau báo "data đang được dùng".
- [ ] Windows: thư mục cạnh `.exe` không ghi được → hiện lỗi + chọn thư mục khác, không tự chuyển sang AppData (Plan §3.1).
- [ ] macOS: chạy từ `~/Downloads` (bị translocate) → màn hướng dẫn kéo vào Applications; sau khi kéo → bước chọn data-root, con trỏ ghi đúng `~/Library/Application Support/WriteStoryApp/data-root.json`.
- [ ] Token không xuất hiện trong URL, log Rust, log Python, stdout/stderr đã lưu.
- [ ] Request thiếu token → 401; `Host` sai → 400 hoặc từ chối; `Origin` lạ → 403; preflight từ origin hợp lệ → 204.
- [ ] Thoát bằng nút đóng, Cmd+Q, Alt+F4, kill tiến trình Tauri (Windows) → không còn tiến trình `writestory-backend` sau thời hạn shutdown (kiểm bằng Task Manager/`ps`).
- [ ] Kill backend khi đang chạy → FE hiện màn "Backend dừng bất ngờ" kèm mã thoát và nút "Khởi động lại"; khởi động lại thành công, cổng mới, token mới.
- [ ] Spike: 3 luồng mock stream song song qua `/v1/events`, editor vẫn gõ được; số đo startup lạnh, RAM idle, dung lượng bundle được ghi vào ADR (không đặt ngưỡng trước khi đo).
- [ ] Quyết định giữ Tauri hay chuyển Electron được ghi ADR `docs/adr/` (Plan §2, §9 G0).
- [ ] Các test luồng liên quan pass: [T01](../../tests/flows/T01-khoi-dong-va-data-root.md); phần stream của [T17](../../tests/flows/T17-phong-viet-va-su-kien.md) chạy được với mock.

## Rủi ro và câu hỏi mở

- Plan §2 nói "launcher sidecar có hậu tố target-triple" nhưng đồng thời đặt PyInstaller onedir trong `bundle.resources`. Thiết kế ở đây spawn trực tiếp file thực thi onedir từ resources bằng `std::process::Command` (để kiểm soát stdin/stdout, Job Object); `externalBin` chỉ thử so sánh trong spike. Cần chốt ở ADR R0.
- Windows khi cạnh `.exe` không ghi được: Plan §3.1 chỉ nói "chọn thư mục data có quyền ghi" nhưng không nói lưu lựa chọn ở đâu (con trỏ chỉ được mô tả cho macOS). Đề xuất con trỏ `%APPDATA%\WriteStoryApp\data-root.json` chỉ dùng trong trường hợp này — cần đồng bộ Plan §3.1.
- Bản portable dạng zip không chạy installer nên `offlineInstaller` không áp dụng; chỉ `fixedRuntime` hoặc dựa vào WebView2 có sẵn (Windows 11). Plan §10 ghi "portable … chọn `offlineInstaller` hoặc `fixedRuntime`" cần làm rõ.
- Tên khóa `fixedRuntime` trong schema Tauri chưa xác nhận (Plan §22, UI §10).
- Origin thực tế của Tauri 2 trên Windows (`http://tauri.localhost`) và macOS (`tauri://localhost`) cần xác nhận trong spike; WKWebView gọi `http://127.0.0.1` từ scheme `tauri://` phải thử thực tế.
- PyInstaller bundle có thể bị Windows Defender/SmartScreen cảnh báo khi chưa ký — ghi nhận ở spike, xử lý ký ở R7.
- Python sinh tiến trình con trước khi Rust gắn vào Job Object (khoảng hở rất ngắn sau spawn): chấp nhận vì backend không tạo process con lúc khởi động; ghi rõ trong test.
