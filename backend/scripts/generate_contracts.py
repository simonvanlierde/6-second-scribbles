"""Generate backend-owned contract artifacts.

Writes JSON Schema files under contracts/jsonschema/:
  - server-event.schema.json  (server -> client messages we parse)
  - client-event.schema.json  (client -> server messages we send)
  - server-events/*.schema.json  (one schema per server event type)
  - client-events/*.schema.json  (one schema per client event type)
  - server-events/index.json
  - client-events/index.json

Also writes the canonical OpenAPI document to contracts/openapi.json and the
shared websocket event catalog to contracts/room-events.json.

Run from the backend directory:
    uv run python -m scripts.generate_contracts
"""

from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from shutil import rmtree
from typing import TYPE_CHECKING, Any, Protocol, cast

from app.core.logging import configure_logging
from app.main import application
from app.rooms.protocol import CLIENT_EVENT_ADAPTER, CONTRACT_EVENT_CATALOG, SERVER_EVENT_ADAPTER

if TYPE_CHECKING:
    from collections.abc import Mapping

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


def write_event_catalog(path: Path) -> None:
    """Write the generated websocket event catalog for frontend metadata."""
    path.write_text(f"{json.dumps(CONTRACT_EVENT_CATALOG, indent=2)}\n")
    logger.info("wrote %s", path)


def write_openapi(path: Path) -> None:
    """Write the canonical OpenAPI document."""
    path.write_text(f"{json.dumps(application.openapi(), indent=2, sort_keys=True)}\n")
    logger.info("wrote %s", path)


def assert_catalog_matches_index(index: dict[str, str], catalog: Mapping[str, object], direction: str) -> None:
    """Ensure backend-owned metadata covers exactly the known event types."""
    if sorted(index) != sorted(catalog):
        msg = f"{direction} event catalog does not match schema types."
        raise ValueError(msg)


def main() -> None:
    """Export shared client/server websocket schemas and OpenAPI docs."""
    out_dir = CONTRACTS_ROOT / "jsonschema"
    out_dir.mkdir(parents=True, exist_ok=True)

    server_schema = generate_schema(cast("SchemaAdapter", SERVER_EVENT_ADAPTER), mode="serialization")
    client_schema = generate_schema(cast("SchemaAdapter", CLIENT_EVENT_ADAPTER), mode="validation")
    server_event_schemas, server_index = split_union_schema(server_schema)
    client_event_schemas, client_index = split_union_schema(client_schema)
    assert_catalog_matches_index(client_index, CONTRACT_EVENT_CATALOG["client"], "client")
    assert_catalog_matches_index(server_index, CONTRACT_EVENT_CATALOG["server"], "server")

    write_schema(server_schema, out_dir / "server-event.schema.json")
    write_schema(client_schema, out_dir / "client-event.schema.json")
    write_event_schemas(server_event_schemas, server_index, out_dir / "server-events")
    write_event_schemas(client_event_schemas, client_index, out_dir / "client-events")
    write_event_catalog(CONTRACTS_ROOT / "room-events.json")
    write_openapi(CONTRACTS_ROOT / "openapi.json")


if __name__ == "__main__":
    main()
