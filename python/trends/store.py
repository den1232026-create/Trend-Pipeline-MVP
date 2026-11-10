"""Read/write Trend JSON files under data/trends/{id}.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parents[1]


def data_dir() -> Path:
    """Resolve data/trends per shared/contracts storage layout."""
    override = os.environ.get("DATA_DIR")
    if override:
        path = Path(override)
        if not path.is_absolute():
            path = _REPO_ROOT / path
        if path.name == "trends":
            return path
        return path / "trends"
    return _REPO_ROOT / "data" / "trends"


def ensure_data_dir() -> Path:
    path = data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def trend_path(trend_id: str) -> Path:
    safe = trend_id.replace("/", "_").replace("\\", "_")
    return ensure_data_dir() / f"{safe}.json"


def write_trend(trend: dict[str, Any]) -> Path:
    path = trend_path(trend["id"])
    path.write_text(
        json.dumps(trend, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def write_trends(trends: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for trend in trends:
        write_trend(trend)
        ids.append(trend["id"])
    return ids


def clear_trends() -> None:
    directory = ensure_data_dir()
    for path in directory.glob("*.json"):
        try:
            path.unlink()
        except OSError:
            continue


def replace_trends(trends: list[dict[str, Any]]) -> list[str]:
    """Atomic-ish refresh: clear data/trends then write the new early set."""
    clear_trends()
    return write_trends(trends)


def list_trends() -> list[dict[str, Any]]:
    directory = ensure_data_dir()
    trends: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            trends.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return trends


def get_trend(trend_id: str) -> dict[str, Any] | None:
    path = trend_path(trend_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_seed_trends() -> list[dict[str, Any]]:
    seed_path = _PACKAGE_DIR / "seed_trends.json"
    raw = json.loads(seed_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("seed_trends.json must be a JSON array")
    return raw
