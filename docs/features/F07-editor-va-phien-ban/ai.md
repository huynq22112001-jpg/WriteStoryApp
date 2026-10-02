# F07 — AI

Không áp dụng – lý do: editor, autosave, working copy, revision, diff và restore là thao tác dữ liệu xác định, không gọi model. Việc áp các thao tác sửa cục bộ do AI đề xuất (`ops: [{paragraph_id, action: replace | insert_after | delete, text}]`, Plan §23.1.B) do **BE** thực hiện trong luồng candidate của F11, không nằm trong package AI và không nằm trong editor.

## Ranh giới với phần AI ở tính năng khác

| F07 cung cấp | Bên dùng | Ghi chú |
|---|---|---|
| `paragraph_id` ổn định cho mọi đoạn (Tiptap UniqueID, giữ nguyên ở BE) | AI nhận văn bản dạng `[p:<id>] nội dung…`; findings trích dẫn theo `paragraph_id` (F10, F11) | Plan §23.1.B, §5 `findings` |
| `chapter_revisions.paragraphs_json`, `plain_text` | `tail_text`, handoff, settle, FTS (F09, F10) | Projection bất biến theo revision |
| `new_paragraph_id()`, `project_doc()` ở `be/.../modules/chapters/domain.py` | F11 áp `ops`, sinh ID cho đoạn chèn, kiểm đoạn ngoài phạm vi không đổi | Không cài trong `ai/` để AI không phụ thuộc định dạng Tiptap |
| `snapshot_if_dirty()` | F11 trước/sau khi nhận candidate (Plan §23.2 #2) | — |

Candidate AI không bao giờ được stream vào editor (UI §1 #3, §6 #1); editor chỉ nhận nội dung sau khi người dùng nhận candidate (F11) dưới dạng một transaction.

## Tên mới đề xuất

Không có.
