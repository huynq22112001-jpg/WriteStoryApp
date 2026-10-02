# Tài liệu WriteStoryApp

App desktop viết truyện bằng AI: React (FE) + Python FastAPI (BE) + package AI Python, chạy local trên Windows/macOS. Hai yêu cầu cốt lõi: **chạy đồng thời nhiều truyện** và **trong một truyện viết tuần tự từng chương, nội dung liền mạch**. Đa ngôn ngữ về kiến trúc, **tiếng Việt làm trước**.

## Tài liệu tổng thể

| File | Nội dung |
|---|---|
| [implementation-plan.vi.md](./implementation-plan.vi.md) | Kế hoạch gốc: phạm vi, stack, runtime, đồng thời, dữ liệu, pipeline AI, API, lộ trình, ma trận tính năng, luồng nghiệp vụ, §23 phần bổ sung |
| [folder-architecture.vi.md](./folder-architecture.vi.md) | Cấu trúc thư mục `fe/`, `be/`, `ai/`, `desktop/`, quy tắc phụ thuộc |
| [ui-design.vi.md](./ui-design.vi.md) | Bố cục giao diện, wireframe, thư viện React |
| [review-and-optimization.vi.md](./review-and-optimization.vi.md) | Rà soát thiết kế, phân tích luồng chương InkOS, kiểm chứng web, nguồn nghiên cứu |
| [inkos-source-inventory.json](./inkos-source-inventory.json) | Chỉ mục nguồn InkOS để đối chiếu |

## Tài liệu triển khai (chia nhỏ)

| Thư mục | Nội dung |
|---|---|
| [features/](./features/README.md) | 15 tính năng MVP (F00–F14), mỗi tính năng có `README.md`, `be.md`, `fe.md`, `ai.md` |
| [tests/](./tests/README.md) | 17 luồng test (T01–T17), cấp độ test, mock provider, dữ liệu mẫu |
| [steps/](./steps/README.md) | Các bước R0 (S00–S10) và [TRANG-THAI.md](./steps/TRANG-THAI.md): đã làm tới đâu, code nào đã có |
| [prompts/](./prompts/README.md) | 136 prompt, mỗi file một prompt (`Pxxx-<tên>.md`), để dán vào nhiều cửa sổ; quy tắc chung, làn chạy song song, bảng tiến độ |

## Cách dùng khi code

1. Chọn tính năng theo thứ tự trong [features/README.md](./features/README.md#thứ-tự-làm-đề-xuất).
2. Đọc `README.md` của tính năng → làm theo checklist trong `be.md`, `ai.md`, `fe.md`.
3. Viết test theo các luồng liên kết trong mục "Tiêu chí hoàn thành"; luồng pass mới đánh dấu tính năng `verified`.
4. Đổi tên bảng/API/hành vi thì cập nhật cả file tính năng và tài liệu tổng thể.
