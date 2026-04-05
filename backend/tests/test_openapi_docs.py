from __future__ import annotations

from app.main import app
from app.core.config import settings


def _has_meaningful_schema(schema: dict | None) -> bool:
    if not schema:
        return False

    if "$ref" in schema:
        return True

    for key in ("type", "properties", "items", "oneOf", "anyOf", "allOf"):
        if schema.get(key):
            return True

    return False


def _resolve_schema(openapi_schema: dict, schema: dict | None) -> dict:
    if not schema:
        return {}

    ref = schema.get("$ref")
    if not ref:
        return schema

    _, _, component_path = ref.partition("#/")
    resolved = openapi_schema
    for segment in component_path.split("/"):
        resolved = resolved[segment]
    return resolved


def test_all_routes_have_openapi_metadata_and_documented_success_responses():
    openapi_schema = app.openapi()
    missing = []

    for path, path_item in openapi_schema["paths"].items():
        if path != "/" and not path.startswith(settings.API_V1_STR):
            continue

        for method, operation in path_item.items():
            if method == "parameters":
                continue

            identifier = f"{method.upper()} {path}"

            if not operation.get("summary"):
                missing.append(f"{identifier} missing summary")
            if not operation.get("description"):
                missing.append(f"{identifier} missing description")
            if not operation.get("tags"):
                missing.append(f"{identifier} missing tags")

            success_codes = [
                code for code in operation.get("responses", {}) if code.startswith("2")
            ]
            if not success_codes:
                missing.append(f"{identifier} missing 2xx response")
                continue

            primary_success = operation["responses"][sorted(success_codes)[0]]
            content = primary_success.get("content", {})
            json_schema = content.get("application/json", {}).get("schema")
            binary_schema = content.get("image/jpeg", {}).get("schema")

            if content and not (
                _has_meaningful_schema(json_schema)
                or _has_meaningful_schema(binary_schema)
            ):
                missing.append(f"{identifier} missing response schema")

    assert missing == []


def test_auth_me_response_schema_documents_authenticated_user_shape():
    openapi_schema = app.openapi()
    operation = openapi_schema["paths"][f"{settings.API_V1_STR}/auth/me"]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    resolved = _resolve_schema(openapi_schema, response_schema)

    assert resolved.get("type") == "object"
    assert {"id", "email", "role", "full_name"} <= set(
        resolved.get("properties", {}).keys()
    )
