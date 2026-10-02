# F13 — AI

Không áp dụng – lý do: export và backup/restore là thao tác dữ liệu xác định do BE sở hữu (Plan §5, FL25; Arch §5 `infrastructure/files/export.py`, `backup.py`). Không gọi model, không có prompt hay structured output. Chuẩn hóa NFC khi xuất dùng `normalizer` của gói ngôn ngữ `vi` (Plan §6.6) như một hàm thuần, không phải workflow AI.
