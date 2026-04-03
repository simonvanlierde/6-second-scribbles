"""Generate shared websocket contract artifacts from Pydantic protocol models.

Writes two JSON Schema files under contracts/jsonschema/:
  - server-event.schema.json  (server → client messages we parse)
  - client-event.schema.json  (client → server messages we send)

The schemas are post-processed to:
  1. Add const-valued fields (like `type`) to required[] — Pydantic omits them
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
from typing import Protocol

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
type JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
type JsonObject = dict[str, JsonValue]


class SchemaAdapter(Protocol):
    """Minimal interface needed from Pydantic type adapters."""

    def json_schema(self, *, by_alias: bool, mode: str) -> JsonObject:
        """Return the adapter's JSON schema."""


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
        required = {
            field_name
            for field_name in required_values
            if isinstance(required_values, list) and isinstance(field_name, str)
        }
        for field_name, field_schema in props.items():
            if isinstance(field_schema, dict) and CONST_KEY in field_schema:
                required.add(field_name)
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
    inlined = _inline_refs(schema, defs)
    inlined.pop("$defs", None)
    return _normalize_schema(inlined)


def write_schema(adapter: SchemaAdapter, path: Path, *, mode: str) -> None:
    """Generate and write a pre-processed schema file."""
    raw_schema = adapter.json_schema(by_alias=True, mode=mode)
    path.write_text(f"{json.dumps(prepare(raw_schema), indent=2)}\n")
    logger.info("wrote %s", path)


def main() -> None:
    """Export shared client/server websocket schemas for contract consumers."""
    out_dir = Path(__file__).parent.parent.parent / "contracts" / "jsonschema"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_schema(SERVER_EVENT_ADAPTER, out_dir / "server-event.schema.json", mode="serialization")
    write_schema(CLIENT_EVENT_ADAPTER, out_dir / "client-event.schema.json", mode="validation")


if __name__ == "__main__":
    main()
