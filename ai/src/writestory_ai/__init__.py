"""WriteStoryApp AI package.

Không import `writestory_be`, FastAPI hay ORM (folder-architecture §6). BE gọi package này
qua contracts và ports; AI trả candidate/đề xuất, BE quyết định lưu.
"""

__version__ = "0.1.0"
