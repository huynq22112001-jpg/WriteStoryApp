import uuid


def new_id() -> str:
    """ID UUIDv7 dạng text, sắp xếp được theo thời gian tạo (Plan §24 D19)."""
    return str(uuid.uuid7())
