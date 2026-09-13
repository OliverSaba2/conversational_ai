"""Load/save a JSON file, tolerating a missing or corrupt file."""

import json
import os


def resolve_path(configured_path: str) -> str:
    if os.path.isabs(configured_path):
        return configured_path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), configured_path)


def load(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save(path: str, data) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
