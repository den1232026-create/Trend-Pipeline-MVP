"""Trends agent: Reddit rising → early Trend JSON (shared/contracts.md)."""

from __future__ import annotations

import logging
from typing import Any

from trends import store
from trends.normalize import posts_to_trends
from trends.reddit_client import RedditConfigError, fetch_posts, has_reddit_creds

logger = logging.getLogger(__name__)

__all__ = ["refresh", "list_trends", "get_trend"]


def list_trends() -> list[dict[str, Any]]:
    trends = store.list_trends()
    # Prefer early_score when present (stage 2), else velocity
    return sorted(
        trends,
        key=lambda t: (
            {"emerging": 0, "rising": 1, "peak": 2}.get(t.get("stage") or "peak", 9),
            -float((t.get("signals") or {}).get("early_score") or 0),
            -float((t.get("signals") or {}).get("upvote_velocity") or 0),
        ),
    )


def get_trend(trend_id: str) -> dict[str, Any] | None:
    return store.get_trend(trend_id)


def _ensure_contract(trends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Force Trends-owned fields: source=reddit, llm_brief always null."""
    for trend in trends:
        trend["llm_brief"] = None
        trend["source"] = "reddit"
        if "signals" not in trend or not isinstance(trend["signals"], dict):
            trend["signals"] = {}
        if "references" not in trend or not trend["references"]:
            raise ValueError(f"Trend {trend.get('id')} missing references")
    return trends


def _write_seed(reason: str) -> dict[str, Any]:
    logger.warning("Trends refresh using seed: %s", reason)
    trends = _ensure_contract(store.load_seed_trends())
    ids = store.replace_trends(trends)
    return {
        "count": len(ids),
        "ids": ids,
        "source": "seed",
        "reason": reason,
    }


def refresh() -> dict[str, Any]:
    """Ingest Reddit rising (early) or seed fallback. Writes data/trends/{id}.json.

    Returns dict with count, ids, source ('reddit'|'seed'), optional reason.
    """
    if not has_reddit_creds():
        return _write_seed("missing REDDIT_* credentials")

    try:
        posts = fetch_posts()
        if not posts:
            return _write_seed("Reddit returned no early posts")
        trends = _ensure_contract(posts_to_trends(posts))
        ids = store.replace_trends(trends)
        stages = {}
        for t in trends:
            stages[t.get("stage") or "?"] = stages.get(t.get("stage") or "?", 0) + 1
        logger.info(
            "Wrote %s live early trends from Reddit (stages=%s)",
            len(ids),
            stages,
        )
        return {
            "count": len(ids),
            "ids": ids,
            "source": "reddit",
            "stages": stages,
        }
    except RedditConfigError as exc:
        return _write_seed(str(exc))
    except Exception as exc:  # noqa: BLE001 — seed fallback required
        logger.exception("Reddit ingest failed")
        return _write_seed(f"Reddit API error: {exc}")
