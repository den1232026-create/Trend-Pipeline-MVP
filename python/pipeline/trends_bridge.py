"""Import Trends public API without editing python/trends/. Soft fallback for stage 1."""

from __future__ import annotations

import json
from typing import Any, Callable

from . import store


def _fallback_list_trends() -> list[dict[str, Any]]:
    trends: list[dict[str, Any]] = []
    directory = store.trends_dir()
    for path in sorted(directory.glob("*.json")):
        try:
            trends.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    if trends:
        return trends
    # Seed from shared/examples when data/trends is empty (orchestrator rule).
    example = store.shared_examples_dir() / "trend.json"
    if example.is_file():
        trend = json.loads(example.read_text(encoding="utf-8"))
        store.write_trend_file(trend)
        return [trend]
    return []


def _fallback_get_trend(trend_id: str) -> dict[str, Any] | None:
    trend = store.get_trend_file(trend_id)
    if trend is not None:
        return trend
    example = store.shared_examples_dir() / "trend.json"
    if example.is_file():
        data = json.loads(example.read_text(encoding="utf-8"))
        if data.get("id") == trend_id:
            store.write_trend_file(data)
            return data
    return None


def _fallback_refresh() -> dict[str, Any]:
    """Copy shared example into data/trends if empty; else leave existing files."""
    existing = list(store.trends_dir().glob("*.json"))
    if existing:
        return {"ok": True, "source": "existing", "count": len(existing)}
    example = store.shared_examples_dir() / "trend.json"
    if not example.is_file():
        return {"ok": False, "source": "none", "count": 0}
    trend = json.loads(example.read_text(encoding="utf-8"))
    store.write_trend_file(trend)
    return {"ok": True, "source": "shared/examples/trend.json", "count": 1}


def _load_api() -> tuple[
    Callable[[], list[dict[str, Any]]],
    Callable[[str], dict[str, Any] | None],
    Callable[[], Any],
]:
    try:
        import trends  # type: ignore

        list_fn = getattr(trends, "list_trends", None)
        get_fn = getattr(trends, "get_trend", None)
        refresh_fn = getattr(trends, "refresh", None)
        if callable(list_fn) and callable(get_fn) and callable(refresh_fn):
            return list_fn, get_fn, refresh_fn
    except ImportError:
        pass

    try:
        from trends import store as trends_store  # type: ignore

        list_fn = trends_store.list_trends
        get_fn = trends_store.get_trend

        def refresh_fn() -> dict[str, Any]:
            # Trends package not fully wired yet — seed via their store if available.
            if list_fn():
                return {"ok": True, "source": "trends.store", "count": len(list_fn())}
            if hasattr(trends_store, "load_seed_trends") and hasattr(
                trends_store, "write_trends"
            ):
                seeds = trends_store.load_seed_trends()
                ids = trends_store.write_trends(seeds)
                return {"ok": True, "source": "trends.seed", "count": len(ids)}
            return _fallback_refresh()

        return list_fn, get_fn, refresh_fn
    except ImportError:
        pass

    return _fallback_list_trends, _fallback_get_trend, _fallback_refresh


list_trends, get_trend, refresh = _load_api()
