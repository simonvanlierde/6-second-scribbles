#!/usr/bin/env python3
"""Export JSON Schema from Pydantic WebSocket protocol models.

Writes two JSON Schema files under frontend/src/generated/:
  - server-event.schema.json  (server → client messages we parse)
  - client-event.schema.json  (client → server messages we send)

The schemas are post-processed to:
  1. Add const-valued fields (like `type`) to required[] — Pydantic omits them
     when they have a default value, but they are always present on the wire.
  2. Inline all $ref/$defs so that json-schema-to-zod can process the schema
     without needing a custom $ref resolver.

Run from the repo root:
    python backend/scripts/generate_frontend_types.py
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Union

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import TypeAdapter

from app.rooms.protocol import (
    ClientEvent,
    DrawpadClearEvent,
    DrawStrokeEvent,
    GameCompleteBroadcastEvent,
    HostChangedEvent,
    HostRestoredEvent,
    KickVoteExpiredEvent,
    KickVoteStartedEvent,
    KickVoteUpdatedEvent,
    LanguageUpdatedEvent,
    PadVisibilityEvent,
    PlayerJoinedEvent,
    PlayerKickedEvent,
    PlayerLeftEvent,
    ProtocolErrorEvent,
    ReadyStatusEvent,
    RestartGameEvent,
    RoomStateEvent,
    RoundCompleteBroadcastEvent,
    SettingsUpdateEvent,
    StartGameEvent,
    StartGuessingEvent,
    StartRoundBroadcastEvent,
)

# ServerEvent is everything the backend may broadcast to clients.
# Some of these are client events that the server relays verbatim to all players.
ServerEvent = Union[
    RoomStateEvent,
    PlayerJoinedEvent,
    HostRestoredEvent,
    ProtocolErrorEvent,
    StartRoundBroadcastEvent,
    ReadyStatusEvent,
    HostChangedEvent,
    LanguageUpdatedEvent,
    PlayerLeftEvent,
    KickVoteStartedEvent,
    KickVoteUpdatedEvent,
    KickVoteExpiredEvent,
    PlayerKickedEvent,
    RoundCompleteBroadcastEvent,
    GameCompleteBroadcastEvent,
    # Relayed client events — server broadcasts these verbatim to all players
    StartGameEvent,
    StartGuessingEvent,
    RestartGameEvent,
    SettingsUpdateEvent,
    DrawStrokeEvent,
    DrawpadClearEvent,
    PadVisibilityEvent,
]


def _add_const_to_required(schema: dict[str, Any]) -> None:
    """Pydantic omits fields that have defaults from required[].
    Discriminator fields (those with a `const` value) always appear on the wire,
    so we add them back so that generated TypeScript types reflect reality.
    """
    for def_schema in schema.get("$defs", {}).values():
        props = def_schema.get("properties", {})
        required: set[str] = set(def_schema.get("required", []))
        for field_name, field_schema in props.items():
            if "const" in field_schema:
                required.add(field_name)
        if required:
            def_schema["required"] = sorted(required)


def _clean(obj: Any) -> Any:
    """Inline $refs, strip default from const fields, convert oneOf→anyOf."""
    # Resolve recursively before applying per-node transforms.
    if isinstance(obj, list):
        return [_clean(item) for item in obj]
    if not isinstance(obj, dict):
        return obj

    # Recurse into values first so transforms below see clean children.
    cleaned: dict[str, Any] = {k: _clean(v) for k, v in obj.items()}

    # `const` fields always appear on the wire — the `.default()` that
    # json-schema-to-zod would emit from the `default` key is noise.
    if "const" in cleaned:
        cleaned.pop("default", None)

    # Pydantic emits `oneOf` for discriminated unions. json-schema-to-zod
    # converts `oneOf` to a verbose superRefine pattern instead of z.union().
    # Since our discriminator guarantees at most one variant matches, `anyOf`
    # is semantically identical and produces the cleaner z.union() output.
    if "oneOf" in cleaned:
        cleaned["anyOf"] = cleaned.pop("oneOf")

    return cleaned


def _inline_refs(obj: Any, defs: dict[str, Any]) -> Any:
    """Recursively replace $ref pointers with the referenced definition."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            name = obj["$ref"].replace("#/$defs/", "")
            return _inline_refs(copy.deepcopy(defs[name]), defs)
        return {k: _inline_refs(v, defs) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_inline_refs(item, defs) for item in obj]
    return obj


def prepare(schema: dict[str, Any]) -> dict[str, Any]:
    """Fix required[], inline $refs, then clean up noise for code generation."""
    _add_const_to_required(schema)
    defs = schema.get("$defs", {})
    inlined = _inline_refs(schema, defs)
    inlined.pop("$defs", None)
    return _clean(inlined)


out_dir = Path(__file__).parent.parent.parent / "frontend" / "src" / "generated"
out_dir.mkdir(parents=True, exist_ok=True)

raw_server = TypeAdapter(ServerEvent).json_schema(by_alias=True, mode="serialization")
(out_dir / "server-event.schema.json").write_text(json.dumps(prepare(raw_server), indent=2))
print(f"wrote {out_dir}/server-event.schema.json")

raw_client = TypeAdapter(ClientEvent).json_schema(by_alias=True, mode="validation")
(out_dir / "client-event.schema.json").write_text(json.dumps(prepare(raw_client), indent=2))
print(f"wrote {out_dir}/client-event.schema.json")
