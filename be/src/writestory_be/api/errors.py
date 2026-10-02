import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from writestory_be.core.errors import (
    AppError,
    ErrorAction,
    ErrorCode,
    default_action,
    default_message,
    default_retryable,
)

log = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    code: ErrorCode
    message: str
    detail: dict[str, Any] | None = None
    retryable: bool
    action: ErrorAction | None = None
    request_id: str | None = None


def error_json(
    code: ErrorCode,
    *,
    request_id: str | None,
    status: int,
    detail: dict[str, Any] | None = None,
    message: str | None = None,
    retryable: bool | None = None,
    action: ErrorAction | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        code=code,
        message=message or default_message(code),
        detail=detail,
        retryable=default_retryable(code) if retryable is None else retryable,
        action=default_action(code) if action is None else action,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status, content=jsonable_encoder(body), headers=headers
    )


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


_HTTP_TO_CODE = {401: ErrorCode.UNAUTHORIZED, 404: ErrorCode.NOT_FOUND, 405: ErrorCode.NOT_FOUND}


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_json(
            exc.code,
            request_id=_request_id(request),
            status=exc.status,
            detail=exc.detail,
            message=exc.message,
            retryable=exc.retryable,
            action=exc.action,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {
                "loc": list(err.get("loc", ())),
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors()
        ]
        return error_json(
            ErrorCode.VALIDATION,
            request_id=_request_id(request),
            status=422,
            detail={"fields": fields},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_TO_CODE.get(exc.status_code, ErrorCode.INTERNAL)
        return error_json(code, request_id=_request_id(request), status=exc.status_code)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Không trả stack trace cho client; log đầy đủ kèm request_id để đối chiếu.
        rid = _request_id(request)
        log.exception("Lỗi không mong muốn (request_id=%s)", rid)
        return error_json(
            ErrorCode.INTERNAL, request_id=rid, status=500, detail={"request_id": rid}
        )
