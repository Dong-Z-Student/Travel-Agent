from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


class AgentJsonParseError(ValueError):
    pass


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = strip_json_fence(text.strip())
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        value = decode_first_object(cleaned)

    if not isinstance(value, dict):
        raise AgentJsonParseError("model output is not a JSON object")
    return value


def parse_pydantic_json(text: str, schema: type[T]) -> T:
    try:
        return schema.model_validate(parse_json_object(text))
    except (AgentJsonParseError, ValidationError) as exc:
        raise AgentJsonParseError(str(exc)) from exc


def strip_json_fence(text: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text


def decode_first_object(text: str) -> Any:
    start = text.find("{")
    if start < 0:
        raise AgentJsonParseError("model output does not contain a JSON object")
    decoder = json.JSONDecoder()
    try:
        value, _ = decoder.raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise AgentJsonParseError(str(exc)) from exc
    return value
