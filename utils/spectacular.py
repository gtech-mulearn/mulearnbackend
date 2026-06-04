def _envelope(inner_schema):
    """Wrap a schema in the standard CustomResponse envelope."""
    return {
        "type": "object",
        "properties": {
            "hasError": {"type": "boolean", "default": False, "example": False},
            "statusCode": {"type": "integer", "default": 200, "example": 200},
            "message": {
                "type": "object",
                "properties": {
                    "general": {"type": "array", "items": {"type": "string"}}
                },
            },
            "response": inner_schema,
        },
        "required": ["hasError", "statusCode", "message", "response"],
    }


def custom_postprocessing_hook(result, generator, **kwargs):
    """
    1. Groups endpoints by functional area based on URL structure.
    2. Wraps all 200/201 JSON response schemas in the CustomResponse envelope
       {hasError, statusCode, message, response: <actual data>}.
    """
    paths = result.get("paths", {})

    for path, path_obj in paths.items():
        segments = [s for s in path.split("/") if s]
        tag = "General"
        if len(segments) >= 3 and segments[0] == "api" and segments[1] == "v1":
            if segments[2] == "dashboard" and len(segments) >= 4:
                tag = segments[3].replace("-", " ").title()
            else:
                tag = segments[2].replace("-", " ").title()

        for method, operation in path_obj.items():
            if method.lower() not in ["get", "post", "put", "patch", "delete", "options", "head"]:
                continue

            operation["tags"] = [tag]

            for status_code, response_obj in operation.get("responses", {}).items():
                if str(status_code) not in ("200", "201"):
                    continue
                for media_obj in response_obj.get("content", {}).values():
                    inner = media_obj.get("schema")
                    if not inner:
                        continue
                    # Skip schemas that are already the CustomResponse envelope
                    ref = inner.get("$ref", "")
                    if ref.endswith("/CustomResponse") or ref.endswith("/CustomResponseSerializer"):
                        continue
                    # Skip if already has hasError at top level (already enveloped)
                    if "hasError" in inner.get("properties", {}):
                        continue
                    media_obj["schema"] = _envelope(inner)

    return result
