"""OpenAPI contract extras shared with the frontend generator."""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import TypeAdapter

from writestory_be.api.errors import ErrorResponse
from writestory_be.api.events_schema import PAYLOAD_MODELS, EventEnvelope

_REF_TEMPLATE = "#/components/schemas/{model}"


def _add_schema(components: dict[str, Any], name: str, model: type) -> None:
    schema = TypeAdapter(model).json_schema(ref_template=_REF_TEMPLATE)
    definitions = schema.pop("$defs", {})
    for definition_name, definition in definitions.items():
        components.setdefault(definition_name, definition)
    components[name] = schema


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Build the route schema and add contracts that are not request/response models."""
    if app.openapi_schema is not None:
        return app.openapi_schema

    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    _add_schema(components, "ErrorResponse", ErrorResponse)
    _add_schema(components, "EventEnvelope", EventEnvelope)
    for payload_model in PAYLOAD_MODELS.values():
        _add_schema(components, payload_model.__name__, payload_model)
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            default_response = operation.get("responses", {}).get("default")
            if default_response is not None:
                default_response["content"] = {
                    "application/json": {
                        "schema": {"$ref": f"{_REF_TEMPLATE.format(model='ErrorResponse')}"}
                    }
                }
    app.openapi_schema = schema
    return schema
