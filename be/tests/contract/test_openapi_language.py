from writestory_be.main import create_app


def test_language_api_contracts_are_registered():
    schema = create_app().openapi()
    paths = schema["paths"]
    assert "/v1/languages/{code}/genre-presets" in paths
    assert {"get", "put"} <= set(paths["/v1/languages/{code}/slop-list"])
    assert "post" in paths["/v1/languages/{code}/normalize"]
    assert "post" in paths["/v1/works/{work_id}/text/check"]
    finding = schema["components"]["schemas"]["LanguageFindingOut"]["properties"]
    assert {"check_id", "confidence", "message_key", "params"} <= set(finding)
