# S07 — Desktop Tauri 2

Trạng thái: partial (P009 scaffold và P010 data-root/instance lock hoàn thành; vòng đời backend và FE boot gate còn lại). Tính năng: F00. Phụ thuộc: S03, S04, S06.

## Mục tiêu

Cửa sổ desktop mở FE, tự khởi động backend Python, quản lý data-root và tắt sạch tiến trình.

## Việc cần làm

- [x] Scaffold `desktop/` (pnpm workspace member, `@tauri-apps/cli`), `src-tauri/tauri.conf.json`: `frontendDist: ../../fe/dist`, `devUrl: http://localhost:5173`, CSP và capability tối thiểu (F00 be.md §C).
- [x] Plugin single-instance đăng ký đầu tiên.
- [x] `data_root.rs`: Windows cạnh `.exe` / con trỏ `%APPDATA%` (D20); macOS con trỏ + phát hiện `/AppTranslocation/` (Plan §3.1); kiểm tra ghi, ổ mạng (Windows và macOS), cloud sync; marker `.writestory-data.json`.
- [x] `instance_lock.rs`: khóa `data/.instance.lock` (D24).
- [ ] `backend.rs`: spawn backend (dev: `uv run python -m writestory_be`; release: onedir trong resources – D22), gửi `BootstrapConfig` qua stdin, đọc NDJSON `ready`/`progress`/`fatal`, drain stderr, health check.
- [ ] `win_job.rs`: Job Object kill-on-close.
- [ ] Xử lý `RunEvent::ExitRequested` + `RunEvent::Exit` → `POST /v1/system/shutdown`, chờ, kill.
- [ ] Commands `get_boot_state`, `get_backend_session`, `restart_backend`… và `fe/src/shared/desktop/bridge.ts` gọi Tauri khi chạy trong desktop.
- [ ] Màn boot FE: starting / needs data-root / translocated / crashed.

## Lệnh

```bash
pnpm --filter desktop tauri dev
```

## Tiêu chí xong

Các kịch bản T01 phần desktop: mở app → backend ready; đóng app → không còn tiến trình `writestory-backend`; mở lần hai → focus cửa sổ cũ; kill app (Windows) → backend chết theo.

## Ghi chú

Spec: [F00](../features/F00-nen-tang-desktop/README.md); test [T01](../tests/flows/T01-khoi-dong-va-data-root.md).
