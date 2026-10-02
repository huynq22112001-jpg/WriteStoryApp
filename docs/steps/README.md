# Các bước làm – từ con số 0 tới hết R0

Mỗi bước là một file nhỏ, làm xong bước trước mới sang bước sau. Mỗi file có: mục tiêu, việc cần làm (checklist), lệnh chạy, tiêu chí xong, liên kết tới spec tính năng ([../features/](../features/README.md)) và test ([../tests/](../tests/README.md)).

Trạng thái: `todo` · `doing` · `done` (đã chạy kiểm chứng) · `code-ready` (đã viết code, chưa chạy được do thiếu công cụ).

## R0 – nền móng và spike

| Bước | File | Nội dung | Tính năng | Trạng thái |
|---|---|---|---|---|
Tình trạng thực tế từng file code: [TRANG-THAI.md](./TRANG-THAI.md). Prompt để triển khai ở cửa sổ khác: [../prompts/](../prompts/README.md).

| S00 | [S00-moi-truong.md](./S00-moi-truong.md) | Cài công cụ: Node, pnpm, uv + Python 3.14, Rust, WebView2 | — | Node/pnpm/Rust có sẵn; **thiếu uv + Python** |
| S01 | [S01-khung-monorepo.md](./S01-khung-monorepo.md) | Khung repo: uv workspace, pnpm workspace, gitignore, editorconfig | — | code-ready (chưa `uv sync`) |
| S02 | [S02-base-ai.md](./S02-base-ai.md) | Package `writestory-ai`: contracts, ports, mock provider, gói `vi` cơ bản | F01, F08 | code nháp, **chưa chạy test** |
| S03 | [S03-base-be.md](./S03-base-be.md) | Package `writestory-be`: app factory, lỗi, bảo mật, health, SSE `/v1/events`, bootstrap, SQLite engine | F00, F01, F02 | code nháp, **chưa chạy test** |
| S04 | [S04-base-fe.md](./S04-base-fe.md) | `fe/`: Vite + React + TS + Tailwind, router, query, i18n `vi`, API client, SSE client, màn kiểm tra backend | F00, F01 | code nháp, đã cài deps, **chưa typecheck/test/build** |
| S05 | [S05-hop-dong-openapi.md](./S05-hop-dong-openapi.md) | Xuất OpenAPI từ BE, sinh types TS cho FE | F01 | todo |
| S06 | [S06-chay-dev.md](./S06-chay-dev.md) | Chạy BE dev + FE dev cùng lúc, token dev | F00 | todo |
| S07 | [S07-desktop-tauri.md](./S07-desktop-tauri.md) | `desktop/` Tauri 2: data-root, spawn backend, single-instance, shutdown | F00 | todo |
| S08 | [S08-spike-editor-ime.md](./S08-spike-editor-ime.md) | Tiptap + `paragraph_id` + test bộ gõ tiếng Việt | F07 | todo |
| S09 | [S09-dong-goi-backend.md](./S09-dong-goi-backend.md) | PyInstaller onedir, gắn vào Tauri, ký macOS | F00 | todo |
| S10 | [S10-ket-thuc-r0.md](./S10-ket-thuc-r0.md) | Checklist kết thúc R0 + ADR (Tauri/Electron, spawn, WebView2) | F00 | todo |

## R1 trở đi

Sau R0, làm theo thứ tự tính năng trong [features/README.md](../features/README.md#thứ-tự-làm-đề-xuất): F02 → F03 → F05 → F04 → F07, rồi R2. Mỗi tính năng tách bước theo checklist trong `be.md`, `ai.md`, `fe.md` của nó; khi bắt đầu một tính năng, tạo file bước `Sxx-<tính-năng>.md` theo cùng mẫu dưới đây.

## Mẫu file bước

```markdown
# Sxx — Tên bước
Trạng thái: todo. Tính năng: Fxx. Phụ thuộc: Syy.

## Mục tiêu
## Việc cần làm
- [ ] …
## Lệnh
## Tiêu chí xong
## Ghi chú
```
