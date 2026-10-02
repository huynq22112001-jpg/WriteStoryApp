# S04 — Base FE (`fe/`)

Trạng thái: done. Tính năng: F00 (màn kiểm tra backend), F01 (API client, SSE client). Phụ thuộc: S01.

## Mục tiêu

Ứng dụng React chạy bằng Vite, có khung route, cache dữ liệu, i18n tiếng Việt và lớp gọi API đúng hợp đồng F01, để các tính năng sau chỉ việc thêm feature.

## Việc cần làm

- [x] `fe/package.json`: React 19, Vite 8, TypeScript 5.9 (openapi-typescript yêu cầu TS 5), Tailwind 4 (`@tailwindcss/vite`), TanStack Router + Query, i18next, Zustand, Vitest + Testing Library.
- [x] `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`, `src/styles/global.css`.
- [x] `app/`: `App.tsx`, `router.tsx` (TanStack Router, hash history – UI §4), `providers.tsx` (QueryClient, i18n), `layouts/AppShell.tsx`.
- [x] `shared/desktop/bridge.ts`: `getBackendSession()` – dev đọc `VITE_DEV_BACKEND_URL`/`VITE_DEV_BACKEND_TOKEN`; Tauri thêm ở S07.
- [x] `shared/api/client.ts` (Bearer token, `Idempotency-Key`, parse `ErrorResponse` → `ApiError`), `shared/api/sse.ts` (parser SSE + kết nối lại bằng `Last-Event-ID`).
- [x] `shared/i18n/` với `vi/common.json`, `vi/errors.json`.
- [x] `features/system/`: trang "Trạng thái hệ thống" gọi `/v1/health` và hiện event SSE.
- [x] `features/library/`: trang Thư viện tạm (rỗng, có hướng dẫn).
- [x] Test: parser SSE, ánh xạ lỗi API, render trang thư viện.
- [ ] shadcn/ui (Base UI) + font Fontsource tiếng Việt → bước đầu của F05/F07 (cần chạy `pnpm dlx shadcn init`).

## Lệnh

```bash
pnpm --filter fe test
```

```bash
pnpm --filter fe build
```

```bash
pnpm --filter fe dev
```

## Tiêu chí xong

- Build và test pass.
- `pnpm --filter fe dev` mở được `http://localhost:5173`, trang Thư viện hiện; trang Trạng thái hệ thống báo "chưa kết nối backend" khi BE chưa chạy (không crash).

## Ghi chú

Spec: [F00 fe.md](../features/F00-nen-tang-desktop/fe.md), [F01 fe.md](../features/F01-hop-dong-api-va-su-kien/fe.md), [UI §4](../ui-design.vi.md).
