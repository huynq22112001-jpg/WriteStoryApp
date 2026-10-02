from writestory_be.main import create_app


def test_openapi_includes_error_and_event_contracts_for_all_routes():
    schema = create_app().openapi()
    components = schema["components"]["schemas"]

    assert "ErrorResponse" in components
    assert "EventEnvelope" in components

    for path_item in schema["paths"].values():
        for method, operation in path_item.items():
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
                "trace",
            }:
                continue
            default_response = operation["responses"]["default"]
            error_schema = default_response["content"]["application/json"]["schema"]
            assert error_schema["$ref"] == "#/components/schemas/ErrorResponse"
