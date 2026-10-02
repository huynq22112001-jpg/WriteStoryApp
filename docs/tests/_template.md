# Txx — Tên luồng

Tính năng: Fxx. Nguồn: Plan FLxx/§…. Cấp test chính: integration | e2e-fe | desktop | thủ công.

## Mục đích

Luồng này chứng minh điều gì (1–2 câu).

## Tiền điều kiện và dữ liệu

- Data-root tạm, fixture: `tests/fixtures/...`
- Mock provider: `{…}`

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| Txx-01 | thành công | 1. … 2. … | … | integration | `be/tests/integration/test_....py` |
| Txx-02 | lỗi | … | … | … | … |
| Txx-03 | hủy | … | … | … | … |
| Txx-04 | phục hồi | … | … | … | … |

## Kiểm tra dữ liệu sau test

- DB: …
- Event đã phát: …
- File trong data-root: …

## Tiêu chí pass

- …

## Ghi chú thủ công

Bước không tự động hóa được và cách kiểm (nếu có).
