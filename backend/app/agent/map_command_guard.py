from __future__ import annotations

from typing import Any


ALLOWED_MAP_COMMANDS = {
    "HIGHLIGHT_POIS",
    "ADD_ROUTE",
    "PLAY_ROUTE_ANIMATION",
    "CLEAR_LAYER",
    "FIT_BOUNDS",
    "SET_LAYER_VISIBLE",
}


def validate_map_commands(commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe_commands: list[dict[str, Any]] = []
    for command in commands:
        command_type = command.get("type")
        if command_type not in ALLOWED_MAP_COMMANDS:
            continue
        payload = command.get("payload")
        safe_commands.append(
            {
                "type": command_type,
                "payload": payload if isinstance(payload, dict) else {},
            }
        )
    return safe_commands
