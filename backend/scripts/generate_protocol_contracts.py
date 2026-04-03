"""Generate shared websocket contract artifacts from backend protocol models.

Writes JSON Schema files under contracts/jsonschema/:
  - server-event.schema.json  (server -> client messages we parse)
  - client-event.schema.json  (client -> server messages we send)
  - server-events/*.schema.json  (one schema per server event type)
  - client-events/*.schema.json  (one schema per client event type)
  - server-events/index.json
  - client-events/index.json

The schemas are post-processed to:
  1. Add const-valued fields (like `type`) to required[] - Pydantic omits them
     when they have a default value, but they are always present on the wire.
  2. Inline all $ref/$defs so that json-schema-to-zod can process the schema
     without needing a custom $ref resolver.

Run from the repo root:
    uv run --project backend python backend/scripts/generate_protocol_contracts.py
"""

from __future__ import annotations

import copy
import json
import logging
import sys
from pathlib import Path
from shutil import rmtree
from typing import Any, Protocol, cast

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import configure_logging
from app.rooms.protocol import CLIENT_EVENT_ADAPTER, SERVER_EVENT_ADAPTER

configure_logging()
logger = logging.getLogger(__name__)

CONST_KEY = "const"
REF_KEY = "$ref"
ONE_OF_KEY = "oneOf"
ANY_OF_KEY = "anyOf"
DEFS_PREFIX = "#/$defs/"
type JsonScalar = str | int | float | bool | None
type JsonValue = Any
type JsonObject = dict[str, Any]


class SchemaAdapter(Protocol):
    """Minimal interface needed from Pydantic type adapters."""

    def json_schema(self, *, by_alias: bool, mode: str) -> JsonObject:
        """Return the adapter's JSON schema."""


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


def generate_schema(adapter: SchemaAdapter, *, mode: str) -> JsonObject:
    """Generate one normalized schema from a Pydantic adapter."""
    raw_schema = adapter.json_schema(by_alias=True, mode=mode)
    return prepare(raw_schema)


def write_schema(schema: JsonObject, path: Path) -> None:
    """Write one pre-processed schema file."""
    path.write_text(f"{json.dumps(schema, indent=2)}\n")
    logger.info("wrote %s", path)


def _event_type_for_schema(schema: JsonObject) -> str:
    """Return the discriminator value for one event schema branch."""
    props = schema.get("properties")
    if not isinstance(props, dict):
        msg = "Event schema is missing properties."
        raise TypeError(msg)

    type_schema = props.get("type")
    if not isinstance(type_schema, dict):
        msg = "Event schema is missing the type property."
        raise TypeError(msg)

    event_type = type_schema.get(CONST_KEY)
    if not isinstance(event_type, str):
        msg = "Event schema type property is missing const."
        raise TypeError(msg)
    return event_type


def split_union_schema(union_schema: JsonObject) -> tuple[list[JsonObject], dict[str, str]]:
    """Return one schema variant per event type plus its index mapping."""
    variants = union_schema.get(ANY_OF_KEY)
    if not isinstance(variants, list):
        msg = f"Expected schema to contain {ANY_OF_KEY}."
        raise TypeError(msg)

    event_schemas: list[JsonObject] = []
    index: dict[str, str] = {}
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        event_type = _event_type_for_schema(variant)
        filename = f"{event_type}.schema.json"
        event_schemas.append(variant)
        index[event_type] = filename

    return event_schemas, index


def write_event_schemas(event_schemas: list[JsonObject], index: dict[str, str], out_dir: Path) -> None:
    """Write one per-event schema file for each union variant."""
    if out_dir.exists():
        rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for event_schema in event_schemas:
        event_type = _event_type_for_schema(event_schema)
        filename = index[event_type]
        write_schema(event_schema, out_dir / filename)

    write_index(index, out_dir / "index.json")


def write_index(index: dict[str, str], path: Path) -> None:
    """Write one per-event schema index file."""
    path.write_text(f"{json.dumps(index, indent=2)}\n")
    logger.info("wrote %s", path)


def main() -> None:
    """Export shared client/server websocket schemas for contract consumers."""
    out_dir = Path(__file__).parent.parent.parent / "contracts" / "jsonschema"
    out_dir.mkdir(parents=True, exist_ok=True)

    server_schema = generate_schema(cast("SchemaAdapter", SERVER_EVENT_ADAPTER), mode="serialization")
    client_schema = generate_schema(cast("SchemaAdapter", CLIENT_EVENT_ADAPTER), mode="validation")
    server_event_schemas, server_index = split_union_schema(server_schema)
    client_event_schemas, client_index = split_union_schema(client_schema)

    write_schema(server_schema, out_dir / "server-event.schema.json")
    write_schema(client_schema, out_dir / "client-event.schema.json")
    write_event_schemas(server_event_schemas, server_index, out_dir / "server-events")
    write_event_schemas(client_event_schemas, client_index, out_dir / "client-events")


if __name__ == "__main__":
    main()
