"""Public schema export helpers."""

from __future__ import annotations

from probemcp.mcp_server import schemas

PUBLIC_SCHEMA_MODELS = {
    name: model
    for name, model in vars(schemas).items()
    if isinstance(model, type)
    and hasattr(model, "model_json_schema")
    and name.endswith(("Request", "Data", "Error"))
}


def export_public_json_schemas() -> dict[str, object]:
    """Return JSON Schemas for public ProbeMCP request/response models."""

    return {name: model.model_json_schema() for name, model in sorted(PUBLIC_SCHEMA_MODELS.items())}
