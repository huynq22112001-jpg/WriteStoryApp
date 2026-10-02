# S05 — Hợp đồng OpenAPI → TypeScript

Trạng thái: done. Tính năng: F01. Phụ thuộc: S03, S04.

## Mục tiêu

FE dùng type sinh từ BE, không tự khai báo DTO trùng lặp (Plan §8, Arch §7).

## Việc cần làm

- [x] `tools/contracts/export_openapi.py`: gọi `create_app(None)` (không side effect), ghi `contracts/openapi.json` (sort keys, indent 2).
- [x] Script FE `gen:api` = `openapi-typescript ../contracts/openapi.json -o src/shared/api/generated/schema.d.ts`.
- [x] Chạy lần đầu, tạo `contracts/openapi.json` và file generated.
- [x] `tools/contracts/check_contracts.py`: export + gen, fail khi artifact thay đổi sau khi tái sinh.
- [x] Chèn `EventEnvelope` và `ErrorResponse` vào `components.schemas` (F01 be.md §D).

## Lệnh

```bash
uv run python tools/contracts/export_openapi.py
```

```bash
pnpm --filter fe gen:api
```

## Tiêu chí xong

`fe/src/shared/api/generated/schema.d.ts` có type của `/v1/health` và `ErrorResponse`; chạy lại hai lệnh không tạo diff.
