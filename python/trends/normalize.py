"""Normalize Reddit posts into Trend dicts matching shared/contracts.md."""

from __future__ import annotations

import re
import time
from typing import Any

from trends.classify import (
    classify_stage,
    classify_trend_type,
    early_priority_score,
)

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
_STAGE_ORDER = {"emerging": 0, "rising": 1, "peak": 2}


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _age_hours(created_utc: float, now: float | None = None) -> float:
    now = now if now is not None else time.time()
    return max((now - created_utc) / 3600.0, 0.0)


def make_trend_id(subreddit: str, post_id: str) -> str:
    sub = subreddit.lower().removeprefix("r/")
    return f"reddit_{sub}_{post_id}"


def post_to_reference(post: dict[str, Any]) -> dict[str, Any]:
    permalink = post.get("permalink") or ""
    if permalink.startswith("http"):
        url = permalink
    elif permalink:
        url = f"https://www.reddit.com{permalink}"
    else:
        url = post.get("url") or ""
    return {
        "url": url,
        "title": post.get("title") or "",
        "score": int(post.get("score") or 0),
        "created_utc": float(post.get("created_utc") or 0),
    }


def _overlap_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster_posts(posts: list[dict[str, Any]], max_refs: int = 3) -> list[list[dict[str, Any]]]:
    """Group posts by title token overlap; each cluster becomes one Trend."""
    remaining = list(posts)
    clusters: list[list[dict[str, Any]]] = []
    while remaining:
        seed = remaining.pop(0)
        seed_tok = _tokens(seed.get("title") or "")
        cluster = [seed]
        kept: list[dict[str, Any]] = []
        for post in remaining:
            if len(cluster) >= max_refs:
                kept.append(post)
                continue
            if _overlap_score(seed_tok, _tokens(post.get("title") or "")) >= 0.35:
                cluster.append(post)
            else:
                kept.append(post)
        remaining = kept
        clusters.append(cluster)
    return clusters


def build_trend_from_cluster(
    cluster: list[dict[str, Any]],
    rising_rank: int,
    now: float | None = None,
) -> dict[str, Any]:
    now = now if now is not None else time.time()
    # Prefer youngest high-velocity post as primary (early catch)
    def _primary_key(p: dict[str, Any]) -> tuple[float, float]:
        created = float(p.get("created_utc") or now)
        age = _age_hours(created, now)
        score = int(p.get("score") or 0)
        vel = score / max(age, 0.5)
        return (vel, -age)

    primary = max(cluster, key=_primary_key)
    sub = (primary.get("subreddit") or "unknown").lower().removeprefix("r/")
    post_id = str(primary.get("id") or "unknown")
    created = float(primary.get("created_utc") or now)
    age_h = _age_hours(created, now)
    score = int(primary.get("score") or 0)
    velocity = round(score / max(age_h, 0.5), 2)
    feed = primary.get("feed") or "rising"
    rank = int(primary.get("rising_rank") or rising_rank)

    signals: dict[str, Any] = {
        "score": score,
        "num_comments": int(primary.get("num_comments") or 0),
        "upvote_ratio": float(primary.get("upvote_ratio") or 0) or None,
        "rising_rank": rank,
        "upvote_velocity": velocity,
    }
    title = primary.get("title") or "Untitled trend"
    trend_type = classify_trend_type(title, sub)
    stage = classify_stage(signals, age_h)
    early = early_priority_score(
        stage=stage,
        signals=signals,
        age_hours=age_h,
        trend_type=trend_type,
        title=title,
        cluster_size=len(cluster),
    )
    signals["early_score"] = early

    refs = [post_to_reference(p) for p in sorted(
        cluster,
        key=lambda p: float(p.get("created_utc") or 0),
        reverse=True,
    )[:3]]

    summary = (
        f"Early-format signal on r/{sub} ({feed}): «{title[:110]}». "
        f"{len(refs)} reference(s); age≈{round(age_h, 1)}h."
    )
    why = (
        f"early_score={early}; stage={stage}; feed={feed}; "
        f"upvote_velocity={velocity}; rising_rank={rank}; "
        f"score={score}; age_h={round(age_h, 1)}; cluster_size={len(refs)}. "
        f"Prioritized before peak for GPTunnel-style catch."
    )
    return {
        "id": make_trend_id(sub, post_id),
        "title": title,
        "summary": summary,
        "source": "reddit",
        "references": refs,
        "signals": signals,
        "stage": stage,
        "trend_type": trend_type,
        "why_trending": why,
        "llm_brief": None,
    }


def _sort_early(trends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        trends,
        key=lambda t: (
            _STAGE_ORDER.get(t.get("stage") or "peak", 9),
            -float((t.get("signals") or {}).get("early_score") or 0),
            -float((t.get("signals") or {}).get("upvote_velocity") or 0),
        ),
    )


def posts_to_trends(
    posts: list[dict[str, Any]],
    *,
    max_trends: int = 12,
) -> list[dict[str, Any]]:
    clusters = cluster_posts(posts)
    trends: list[dict[str, Any]] = []
    for idx, cluster in enumerate(clusters, start=1):
        trends.append(build_trend_from_cluster(cluster, rising_rank=idx))

    trends = _sort_early(trends)

    # Prefer early stages: keep peak only if we lack enough emerging/rising
    early = [t for t in trends if t.get("stage") in ("emerging", "rising")]
    peak = [t for t in trends if t.get("stage") == "peak"]
    if len(early) >= 3:
        selected = early[:max_trends]
    else:
        selected = (early + peak)[:max_trends]
    return _sort_early(selected)
