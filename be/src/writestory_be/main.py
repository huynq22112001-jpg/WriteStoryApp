"""App factory. `create_app` không mở vault, không migrate, không chạy job (Arch §7):
side effect thuộc bootstrap/runtime, nhờ vậy xuất OpenAPI an toàn."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from writestory_be import __version__
from writestory_be.api import streams
from writestory_be.api.errors import ErrorResponse, install_exception_handlers
from writestory_be.api.request_id import RequestIdMiddleware
from writestory_be.api.security import LocalSecurityMiddleware
from writestory_be.bootstrap.context import Runtime
from writestory_be.modules.dev import router as dev_router
from writestory_be.modules.system import router as system_router

_ERROR_RESPONSES: dict[int | str, dict] = {"default": {"model": ErrorResponse}}


def _operation_id(route: APIRoute) -> str:
    return route.name


def create_app(runtime: Runtime | None = None) -> FastAPI:
    runtime = runtime or Runtime.for_schema_export()
    dev = runtime.config.dev_features

    app = FastAPI(
        title="WriteStoryApp backend",
        version=__version__,
        docs_url="/docs" if dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if dev else None,
        generate_unique_id_function=_operation_id,
    )
    app.state.runtime = runtime

    install_exception_handlers(app)
    app.include_router(system_router.router, responses=_ERROR_RESPONSES)
    app.include_router(streams.router, responses=_ERROR_RESPONSES)
    if dev:
        app.include_router(dev_router.router, responses=_ERROR_RESPONSES)

    # add_middleware: middleware thêm sau nằm ngoài. Thứ tự chạy: CORS → RequestId → Security.
    app.add_middleware(LocalSecurityMiddleware, runtime=runtime)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime.config.allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "Last-Event-ID"],
        expose_headers=["Retry-After", "X-Request-Id"],
        allow_credentials=False,
    )
    return app
