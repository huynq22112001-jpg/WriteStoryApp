"""Bảo vệ API loopback (Plan §3, F00 be.md §C).

Thứ tự middleware (ngoài → trong): CORS → RequestId → LocalSecurity → router.
- `Host` phải là `127.0.0.1:<port>` (chống DNS rebinding); dev cho thêm `localhost:<port>`.
- `Origin` (nếu có) phải thuộc danh sách từ bootstrap.
- Mọi route cần `Authorization: Bearer <token>`; không nhận token qua query string.
"""

import hmac

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from writestory_be.api.errors import error_json
from writestory_be.bootstrap.context import Runtime
from writestory_be.core.errors import ErrorCode, http_status

# Trang tài liệu API chỉ có khi bật dev_features; trình duyệt không gửi được header token.
_DEV_PUBLIC_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/openapi.json"})


class LocalSecurityMiddleware:
    def __init__(self, app: ASGIApp, *, runtime: Runtime) -> None:
        self.app = app
        self.runtime = runtime
        self._token = runtime.config.token.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        code = self._check(scope, headers)
        if code is not None:
            rid = scope.get("state", {}).get("request_id")
            response = error_json(code, request_id=rid, status=http_status(code))
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _check(self, scope: Scope, headers: Headers) -> ErrorCode | None:
        rt = self.runtime
        allowed_hosts = rt.allowed_hosts()
        if allowed_hosts and headers.get("host") not in allowed_hosts:
            return ErrorCode.FORBIDDEN_HOST

        origin = headers.get("origin")
        if origin is not None and origin not in rt.config.allowed_origins:
            return ErrorCode.FORBIDDEN_ORIGIN

        if rt.config.dev_features and scope["path"] in _DEV_PUBLIC_PATHS:
            return None

        if rt.shutting_down and scope["path"] != "/v1/health":
            return ErrorCode.BACKEND_SHUTTING_DOWN

        auth = headers.get("authorization", "")
        scheme, _, presented = auth.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(
            presented.strip().encode(), self._token
        ):
            return ErrorCode.UNAUTHORIZED
        return None
