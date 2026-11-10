"""Paths and JSON I/O for presets, jobs, artifacts (shared storage layout)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parents[1]


def repo_root() -> Path:
    return _REPO_ROOT


def data_root() -> Path:
    override = os.environ.get("DATA_DIR", "").strip()
    if override:
        path = Path(override)
        if not path.is_absolute():
            path = _REPO_ROOT / path
        return path
    return _REPO_ROOT / "data"


def presets_dir() -> Path:
    path = data_root() / "presets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def jobs_dir() -> Path:
    path = data_root() / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifacts_dir() -> Path:
    path = data_root() / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def trends_dir() -> Path:
    path = data_root() / "trends"
    path.mkdir(parents=True, exist_ok=True)
    return path


def shared_examples_dir() -> Path:
    return _REPO_ROOT / "shared" / "examples"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def preset_path(preset_id: str) -> Path:
    safe = preset_id.replace("/", "_").replace("\\", "_")
    return presets_dir() / f"{safe}.json"


def job_meta_path(job_id: str) -> Path:
    safe = job_id.replace("/", "_").replace("\\", "_")
    return jobs_dir() / f"{safe}.json"


def job_input_dir(job_id: str) -> Path:
    safe = job_id.replace("/", "_").replace("\\", "_")
    path = jobs_dir() / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_preset(preset: dict[str, Any]) -> Path:
    return _write_json(preset_path(preset["id"]), preset)


def get_preset(preset_id: str) -> dict[str, Any] | None:
    path = preset_path(preset_id)
    if not path.is_file():
        return None
    try:
        return _read_json(path)
    except (json.JSONDecodeError, OSError):
        return None


def list_presets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(presets_dir().glob("*.json")):
        try:
            items.append(_read_json(path))
        except (json.JSONDecodeError, OSError):
            continue
    return items


def write_job(job: dict[str, Any]) -> Path:
    return _write_json(job_meta_path(job["id"]), job)


def get_job(job_id: str) -> dict[str, Any] | None:
    path = job_meta_path(job_id)
    if not path.is_file():
        return None
    try:
        return _read_json(path)
    except (json.JSONDecodeError, OSError):
        return None


def write_trend_file(trend: dict[str, Any]) -> Path:
    """Update trend JSON (Pipeline writes llm_brief only)."""
    safe = trend["id"].replace("/", "_").replace("\\", "_")
    path = trends_dir() / f"{safe}.json"
    return _write_json(path, trend)


def get_trend_file(trend_id: str) -> dict[str, Any] | None:
    safe = trend_id.replace("/", "_").replace("\\", "_")
    path = trends_dir() / f"{safe}.json"
    if not path.is_file():
        return None
    try:
        return _read_json(path)
    except (json.JSONDecodeError, OSError):
        return None


def mock_generate_enabled() -> bool:
    raw = os.environ.get("MOCK_GENERATE", "1").strip().lower()
    return raw in ("1", "true", "yes", "on")
