"""Generate backend-owned contract artifacts.

Writes JSON Schema files under contracts/jsonschema/:
  - server-event.schema.json  (server -> client messages we parse)
  - client-event.schema.json  (client -> server messages we send)

Also writes the canonical OpenAPI document to contracts/openapi.json.

Run from the backend directory:
    uv run python -m scripts.generate_contracts
"""

from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from app.core.logging import configure_logging
from app.main import application
from app.rooms.protocol import CLIENT_EVENT_ADAPTER, SERVER_EVENT_ADAPTER

if TYPE_CHECKING:
    from pydantic import TypeAdapter

configure_logging()
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_ROOT = Path(os.environ.get("CONTRACTS_ROOT", REPO_ROOT / "contracts"))
CONST_KEY = "const"
REF_KEY = "$ref"
ONE_OF_KEY = "oneOf"
ANY_OF_KEY = "anyOf"
DEFS_PREFIX = "#/$defs/"
type JsonValue = Any
type JsonObject = dict[str, Any]


def _required_fields(props: JsonObject, required_values: JsonValue) -> set[str]:
    """Return schema required fields, including const-valued properties."""
    required: set[str] = set()
    if isinstance(required_values, list):
        for field_name in required_values:
            if isinstance(field_name, str):
                required.add(field_name)
    for field_name, field_schema in props.items():
        if isinstance(field_schema, dict) and CONST_KEY in field_schema:
            required.add(field_name)
    return required


def _normalize_schema(obj: JsonValue) -> JsonValue:
    """Normalize Pydantic JSON Schema into cleaner json-schema-to-zod input."""
    if isinstance(obj, list):
        return [_normalize_schema(item) for item in obj]
    if not isinstance(obj, dict):
        return obj

    normalized: JsonObject = {key: _normalize_schema(value) for key, value in obj.items()}

    props = normalized.get("properties")
    required_values = normalized.get("required")
    if isinstance(props, dict):
        required = _required_fields(props, required_values)
        if required:
            normalized["required"] = sorted(required)

    if CONST_KEY in normalized:
        normalized.pop("default", None)

    if ONE_OF_KEY in normalized:
        normalized[ANY_OF_KEY] = normalized.pop(ONE_OF_KEY)

    return normalized


def _inline_refs(obj: JsonValue, defs: JsonObject) -> JsonValue:
    """Recursively replace $ref pointers with the referenced definition."""
    if isinstance(obj, dict):
        if REF_KEY in obj and isinstance(obj[REF_KEY], str):
            name = obj[REF_KEY].removeprefix(DEFS_PREFIX)
            return _inline_refs(copy.deepcopy(defs[name]), defs)
        return {k: _inline_refs(v, defs) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_inline_refs(item, defs) for item in obj]
    return obj


def prepare(schema: JsonObject) -> JsonObject:
    """Fix required[], inline $refs, then clean up noise for code generation."""
    defs = schema.get("$defs", {})
    if not isinstance(defs, dict):
        defs = {}
    inlined = cast("JsonObject", _inline_refs(schema, defs))
    inlined.pop("$defs", None)
    return cast("JsonObject", _normalize_schema(inlined))


def generate_schema(adapter: TypeAdapter[Any], *, mode: Literal["validation", "serialization"]) -> JsonObject:
    """Generate one normalized schema from a Pydantic adapter."""
    raw_schema = adapter.json_schema(by_alias=True, mode=mode)
    return prepare(raw_schema)


def write_schema(schema: JsonObject, path: Path) -> None:
    """Write one pre-processed schema file."""
    path.write_text(f"{json.dumps(schema, indent=2)}\n")
    logger.info("wrote %s", path)


def write_openapi(path: Path) -> None:
    """Write the canonical OpenAPI document."""
    path.write_text(f"{json.dumps(application.openapi(), indent=2, sort_keys=True)}\n")
    logger.info("wrote %s", path)


def main() -> None:
    """Export shared client/server websocket schemas and OpenAPI docs."""
    out_dir = CONTRACTS_ROOT / "jsonschema"
    out_dir.mkdir(parents=True, exist_ok=True)

    server_schema = generate_schema(SERVER_EVENT_ADAPTER, mode="serialization")
    client_schema = generate_schema(CLIENT_EVENT_ADAPTER, mode="validation")

    write_schema(server_schema, out_dir / "server-event.schema.json")
    write_schema(client_schema, out_dir / "client-event.schema.json")
    write_openapi(CONTRACTS_ROOT / "openapi.json")


if __name__ == "__main__":
    main()
