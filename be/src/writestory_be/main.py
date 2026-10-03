"""App factory. `create_app` không mở vault, không migrate, không chạy job (Arch §7):
side effect thuộc bootstrap/runtime, nhờ vậy xuất OpenAPI an toàn."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from writestory_be import __version__
from writestory_be.api import streams
from writestory_be.api.errors import ErrorResponse, install_exception_handlers
from writestory_be.api.openapi import custom_openapi
from writestory_be.api.request_id import RequestIdMiddleware
from writestory_be.api.security import LocalSecurityMiddleware
from writestory_be.bootstrap.context import Runtime
from writestory_be.modules.chapters import router as chapters_router
from writestory_be.modules.dev import router as dev_router
from writestory_be.modules.language import router as language_router
from writestory_be.modules.longform import router as longform_router
from writestory_be.modules.memory import router as memory_router
from writestory_be.modules.onboarding import router as onboarding_router
from writestory_be.modules.providers import router as providers_router
from writestory_be.modules.system import router as system_router
from writestory_be.modules.vault import router as vault_router
from writestory_be.modules.works import router as works_router

_ERROR_RESPONSES: dict[int | str, dict] = {"default": {"model": ErrorResponse}}


def _operation_id(route: APIRoute) -> str:
    return route.name


def create_app(runtime: Runtime | None = None) -> FastAPI:
    runtime = runtime or Runtime.for_schema_export()
    dev = runtime.config.dev_features

    @asynccontextmanager
    async def lifespan(_app):
        if runtime.uow is not None:
            from writestory_be.modules.providers.service import ProviderService

            async def discover_enabled_providers():
                service = ProviderService(runtime)
                for provider in await service.list():
                    if provider["enabled"] and provider["auto_discover"]:
                        runtime.spawn(service.discover(provider["id"]))

            runtime.spawn(discover_enabled_providers())

            async def resume_interrupted_writes():
                from sqlalchemy import select

                from writestory_be.infrastructure.db.models.system import Job
                from writestory_be.jobs.handlers.chapter_write import ChapterWriteRunner
                from writestory_be.modules.longform.resync_job import ResyncJobService
                from writestory_be.modules.longform.revise_job import ReviseJobService

                async with runtime.uow.read_sessions() as session:
                    rows = list(
                        (
                            await session.scalars(
                                select(Job)
                                .where(
                                    Job.type.in_(("write", "revise", "resync")),
                                    Job.status == "interrupted",
                                )
                                .order_by(Job.created_at)
                            )
                        ).all()
                    )
                    jobs = [(row.id, row.type) for row in rows]
                for job_id, job_type in jobs:
                    if job_type == "write":
                        runner = getattr(runtime, "chapter_write_runner", None)
                        if runner is None:
                            runner = ChapterWriteRunner(runtime)
                            runtime.chapter_write_runner = runner
                        runtime.spawn(runner.run(job_id))
                    elif job_type == "revise":
                        runtime.spawn(ReviseJobService(runtime).run(job_id))
                    else:
                        runtime.spawn(ResyncJobService(runtime).run(job_id))

            runtime.spawn(resume_interrupted_writes())
        try:
            yield
        finally:
            if runtime.writer_queue is not None:
                await runtime.writer_queue.close()
            if runtime.db_engine is not None:
                await runtime.db_engine.dispose()

    app = FastAPI(
        title="WriteStoryApp backend",
        version=__version__,
        docs_url="/docs" if dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if dev else None,
        generate_unique_id_function=_operation_id,
        lifespan=lifespan,
    )
    app.state.runtime = runtime

    app.openapi = lambda: custom_openapi(app)

    install_exception_handlers(app)
    app.include_router(system_router.router, responses=_ERROR_RESPONSES)
    app.include_router(vault_router.router, responses=_ERROR_RESPONSES)
    app.include_router(onboarding_router.router, responses=_ERROR_RESPONSES)
    app.include_router(works_router.router, responses=_ERROR_RESPONSES)
    app.include_router(language_router, responses=_ERROR_RESPONSES)
    app.include_router(memory_router, responses=_ERROR_RESPONSES)
    app.include_router(longform_router, responses=_ERROR_RESPONSES)
    app.include_router(chapters_router, responses=_ERROR_RESPONSES)
    app.include_router(providers_router, responses=_ERROR_RESPONSES)
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
