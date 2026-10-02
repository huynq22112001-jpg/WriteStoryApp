from typing import Annotated

from fastapi import Depends, Request

from writestory_be.bootstrap.context import Runtime


def get_runtime(request: Request) -> Runtime:
    return request.app.state.runtime


RuntimeDep = Annotated[Runtime, Depends(get_runtime)]
