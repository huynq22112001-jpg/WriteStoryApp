# S00 — Chuẩn bị môi trường

Trạng thái: Node 24.15, pnpm 10.33, Rust 1.98, git 2.53 đã có trên máy dev (02/10/2026). **Thiếu uv và Python** → BE/AI chưa chạy được.

## Mục tiêu

Máy dev có đủ công cụ để build FE, BE, AI và desktop.

## Việc cần làm

- [x] Node ≥ 22.16 (đang có 24.15) và pnpm ≥ 10.
- [x] Rust stable (đang có 1.98) – cần cho S07.
- [ ] uv (quản lý Python, venv, lockfile).
- [ ] CPython 3.14 bản GIL tiêu chuẩn do uv quản lý (Plan §2, §24).
- [ ] Windows: Microsoft C++ Build Tools (Tauri/Rust) và WebView2 Runtime (có sẵn trên Windows 11).
- [ ] macOS (khi build Mac): Xcode Command Line Tools.

## Lệnh

Cài uv trên Windows (PowerShell, cài vào thư mục người dùng, không cần quyền admin):

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Cài Python 3.14 do uv quản lý:

```bash
uv python install 3.14
```

Kiểm tra:

```bash
uv --version && uv run --python 3.14 python --version
```

## Tiêu chí xong

- `uv run python --version` trả 3.14.x trong thư mục repo.
- `pnpm --version`, `cargo --version` chạy được.

## Ghi chú

- Không dùng alias `python` của Microsoft Store; mọi lệnh Python chạy qua `uv run`.
- Không cài Python free-threaded (Plan §2).
