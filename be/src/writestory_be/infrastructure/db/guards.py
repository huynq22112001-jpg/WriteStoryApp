from contextvars import ContextVar

in_write_txn: ContextVar[bool] = ContextVar("in_write_txn", default=False)


def assert_not_in_write_txn() -> None:
    if in_write_txn.get():
        raise RuntimeError("Không được gọi mạng hoặc AI bên trong transaction ghi DB")
