# S06 — Chạy dev BE + FE

Trạng thái: done. Tính năng: F00. Phụ thuộc: S03, S04.

## Mục tiêu

Phát triển FE trong trình duyệt với backend thật, chưa cần Tauri.

## Việc cần làm

- [x] BE `--dev`: data-root `WRITESTORY_DATA_ROOT` hoặc `./data`, cổng `8765`, token `WRITESTORY_DEV_TOKEN` (mặc định `dev-token`), origin cho phép `http://localhost:5173`, bật `/docs`.
- [x] FE `.env.development`: `VITE_DEV_BACKEND_URL=http://127.0.0.1:8765`, `VITE_DEV_BACKEND_TOKEN=dev-token`.
- [x] Script gốc `pnpm dev` chạy song song BE và FE (`tools/dev/run_dev.py`).

## Lệnh

Cửa sổ 1:

```bash
uv run python -m writestory_be --dev
```

Cửa sổ 2:

```bash
pnpm --filter fe dev
```

## Tiêu chí xong

Mở `http://localhost:5173/#/system`: trang báo backend "ok", danh sách sự kiện nhận `backend.notice` lúc kết nối; tắt BE thì FE hiện banner mất kết nối và tự nối lại khi BE chạy lại.

## Ghi chú

Token dev chỉ dùng cho máy dev; bản desktop luôn sinh token ngẫu nhiên mỗi phiên (F00).
