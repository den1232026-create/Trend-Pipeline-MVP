"""Fetch rising (early) posts via praw. Hot only as empty-rising fallback."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from trends.classify import MAX_POST_AGE_H, is_post_too_old

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = ("memes", "aivideo", "StableDiffusion")
# Pull more candidates, then keep the earliest/highest-velocity slice
DEFAULT_TOTAL_LIMIT = 15
CANDIDATE_MULTIPLIER = 2


class RedditConfigError(Exception):
    """Missing or incomplete Reddit credentials."""


def _subreddits() -> list[str]:
    raw = os.environ.get("REDDIT_SUBREDDITS", "").strip()
    if not raw:
        return list(DEFAULT_SUBREDDITS)
    return [s.strip().removeprefix("r/") for s in raw.split(",") if s.strip()]


def has_reddit_creds() -> bool:
    return bool(
        os.environ.get("REDDIT_CLIENT_ID", "").strip()
        and os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
        and os.environ.get("REDDIT_USER_AGENT", "").strip()
    )


def _age_hours(created_utc: float, now: float | None = None) -> float:
    now = now if now is not None else time.time()
    return max((now - created_utc) / 3600.0, 0.0)


def _submission_to_dict(
    submission: Any,
    subreddit: str,
    *,
    feed: str,
    rising_rank: int,
) -> dict[str, Any]:
    permalink = getattr(submission, "permalink", "") or ""
    return {
        "id": str(submission.id),
        "title": submission.title or "",
        "score": int(submission.score or 0),
        "num_comments": int(submission.num_comments or 0),
        "upvote_ratio": float(getattr(submission, "upvote_ratio", 0) or 0),
        "created_utc": float(submission.created_utc or 0),
        "permalink": permalink,
        "url": getattr(submission, "url", "") or "",
        "subreddit": subreddit,
        "feed": feed,
        "rising_rank": rising_rank,
        "stickied": bool(getattr(submission, "stickied", False)),
    }


def _post_velocity(post: dict[str, Any], now: float) -> float:
    age = _age_hours(float(post.get("created_utc") or now), now)
    score = int(post.get("score") or 0)
    return score / max(age, 0.5)


def fetch_posts(total_limit: int = DEFAULT_TOTAL_LIMIT) -> list[dict[str, Any]]:
    """Prefer subreddit.rising; filter stale; rank by velocity × freshness."""
    if not has_reddit_creds():
        raise RedditConfigError(
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT required"
        )

    try:
        import praw
    except ImportError as exc:
        raise RuntimeError(
            "praw is not installed; pip install -r python/requirements.txt"
        ) from exc

    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"].strip(),
        client_secret=os.environ["REDDIT_CLIENT_SECRET"].strip(),
        user_agent=os.environ["REDDIT_USER_AGENT"].strip(),
    )
    reddit.read_only = True

    subs = _subreddits()
    per_sub = max(3, (total_limit * CANDIDATE_MULTIPLIER) // max(len(subs), 1))
    posts: list[dict[str, Any]] = []
    seen: set[str] = set()
    now = time.time()

    for sub_name in subs:
        subreddit = reddit.subreddit(sub_name)
        batch: list[Any] = list(subreddit.rising(limit=per_sub))
        feed = "rising"
        if not batch:
            logger.info("r/%s rising empty — falling back to hot (early slice)", sub_name)
            batch = list(subreddit.hot(limit=per_sub))
            feed = "hot"

        for rank, submission in enumerate(batch, start=1):
            if getattr(submission, "stickied", False):
                continue
            if submission.id in seen:
                continue
            created = float(getattr(submission, "created_utc", 0) or 0)
            age = _age_hours(created, now)
            if is_post_too_old(age):
                continue
            # Hot fallback: keep only young posts so we don't flood with peak
            if feed == "hot" and age > MAX_POST_AGE_H / 2:
                continue
            seen.add(submission.id)
            posts.append(
                _submission_to_dict(
                    submission,
                    sub_name,
                    feed=feed,
                    rising_rank=rank,
                )
            )

    posts.sort(
        key=lambda p: (
            0 if p.get("feed") == "rising" else 1,
            -_post_velocity(p, now),
            float(p.get("created_utc") or 0) * -1,
        )
    )
    return posts[:total_limit]
