# S02 — Base package AI (`writestory-ai`)

Trạng thái: done (25 test pass, Ruff pass, ranh giới AI kiểm tra). Tính năng: F01 (port tiến độ), F08 (gói `vi` cơ bản), F10 (mock provider dùng cho spike). Phụ thuộc: S01.

## Mục tiêu

Package Python độc lập, **không import BE**, có hợp đồng cơ bản để BE gọi và để test mọi luồng bằng mock provider.

## Việc cần làm

- [x] `ai/pyproject.toml` (hatchling, `src` layout, phụ thuộc `pydantic`, `httpx`).
- [x] `contracts/errors.py`: `AIError` + lớp con, mỗi lớp có `code` trùng `ErrorCode` của BE (F01): `PROVIDER_AUTH`, `PROVIDER_UNREACHABLE`, `PROVIDER_RATE_LIMIT`, `PROVIDER_REFUSAL`, `OUTPUT_TRUNCATED`, `STRUCTURED_OUTPUT_INVALID`, `OUTPUT_EMPTY`, `CANCELLED`.
- [x] `contracts/generation.py`: `Message`, `GenerationRequest` (model, system, messages, max_tokens, effort), `StreamEvent` (`text` / `done`), `GenerationResult` (`stop_reason` = `end_turn` | `max_tokens` | `refusal`).
- [x] `contracts/usage.py`: `Usage` (input/output/cache read/cache write, `reported`).
- [x] `contracts/events.py`: `StepProgress`, `TokenDelta` (`candidate_id`, `step`, `offset`, `text`).
- [x] `ports/provider.py` (`TextProvider` Protocol), `ports/progress.py` (`ProgressSink` Protocol).
- [x] `providers/mock.py`: `MockTextProvider` + `MockScenario` (latency, tốc độ token, chuỗi lỗi, refusal, cắt `max_tokens`, văn bản cố định) – đặt trong `src` để bản đóng gói spike dùng được (Plan §24 D23).
- [x] `languages/base.py` (`LanguagePack` Protocol), `languages/registry.py`, `languages/vi/` với `normalizer.py` (NFC, xuống dòng), `length.py` (đếm âm tiết), `search.py` (bỏ dấu + `đ→d`).
- [x] Test unit: đếm âm tiết, fold tìm kiếm (khớp kết quả FTS đã chạy thử ở T13), chuẩn hóa, mock provider (stream, lỗi, refusal, cắt).

## Lệnh

```bash
uv run pytest ai/tests -q
```

```bash
uv run ruff check ai
```

## Tiêu chí xong

- Toàn bộ test `ai/tests` pass.
- `rg "writestory_be" ai/` không có kết quả (AI không import BE – Arch §6).

## Ghi chú

- Provider thật (Anthropic, OpenAI-compatible) làm ở F04; kiểm tra xác định tiếng Việt đầy đủ (xưng hô, lớp từ, chính tả) ở F08.
- Spec: [F08 ai.md](../features/F08-goi-ngon-ngu-vi/ai.md), [F01 ai.md](../features/F01-hop-dong-api-va-su-kien/ai.md), [F00 ai.md](../features/F00-nen-tang-desktop/ai.md).
