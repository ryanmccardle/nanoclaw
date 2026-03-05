# ABOUTME: Provides common JSON parsing and output helpers for write scripts.
# ABOUTME: Centralizes error messages for malformed input payloads.

import json


def load_data(data: str) -> dict:
    if not data:
        raise ValueError("Missing --data payload")
    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc.msg}") from exc


def ensure_id(identifier: str) -> str:
    if not identifier:
        raise ValueError("Missing --id")
    return identifier


def emit_json(payload: dict) -> None:
    print(json.dumps(payload))
