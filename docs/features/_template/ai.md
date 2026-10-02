# Fxx — AI

Nếu tính năng không có phần AI, chỉ ghi: "Không áp dụng – lý do: …" và bỏ các mục dưới.

## Module và file

```text
ai/src/writestory_ai/
  contracts/…
  workflows/…
  languages/vi/prompts/…
```

## Contract (Pydantic)

```text
InputModel:  …
OutputModel: …
```

## Workflow

1. …

## Prompt

| Template ID | Vai trò | Lớp cache (Plan §6.4) | Đầu ra |
|---|---|---|---|
| … | … | … | … |

## Model, effort, giới hạn

- Vai trò (Plan §7.1): …; effort gợi ý: …; `max_tokens`: …
- Structured output: schema …; fallback khi model không hỗ trợ: …

## Lỗi và trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Refusal | … |
| Bị cắt `max_tokens` | … |
| JSON không hợp lệ | … |

## Đánh giá

- Chỉ số / rubric: …
- Bộ dữ liệu mẫu: `tests/fixtures/...`

## Việc cần làm

- [ ] …

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | … | `ai/tests/unit/...` |
| contract (mock provider) | … | `ai/tests/contract/...` |

## Tên mới đề xuất

Ghi "Không có" nếu không có.
