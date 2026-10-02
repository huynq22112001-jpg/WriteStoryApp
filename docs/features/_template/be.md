# Fxx — Backend

## Module và file

```text
be/src/writestory_be/modules/<module>/
  router.py      …
  schemas.py     …
  service.py     …
  domain.py      …
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| … | … | … | … |

Migration: `be/migrations/versions/<rev>_<tên>.py`. Ghi rõ có cần backfill/dữ liệu cũ không.

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| … | … | … | … | … |

## Logic xử lý

1. …
2. …

Quy tắc transaction: …

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| … | … | … |

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| … | … | … |

## Việc cần làm

- [ ] …

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | … | `be/tests/unit/...` |
| integration | … | `be/tests/integration/...` |

## Tên mới đề xuất

Tên bảng/cột/API/code chưa có trong Plan (để đồng bộ lại). Ghi "Không có" nếu không có.
