"""Heuristics for trend stage, type, and early-catch priority (no LLM)."""

from __future__ import annotations

import re
from typing import Any

# Stage thresholds — biased toward catching before peak
EMERGING_MAX_AGE_H = 8.0
RISING_MAX_AGE_H = 24.0
PEAK_MIN_AGE_H = 36.0
MODERATE_SCORE = 400
HIGH_SCORE = 4000
HIGH_VELOCITY = 40.0
EARLY_VELOCITY = 15.0

# Drop stale posts from live ingest (hours)
MAX_POST_AGE_H = 48.0

_FACE_SWAP = re.compile(
    r"\b(face[\s-]?swap|faceswap|reactor|insightface|roop|instantid|"
    r"ip[\s-]?adapter|faceid)\b",
    re.I,
)
_TEMPLATE = re.compile(
    r"\b(template|drake|expanding\s+brain|distracted\s+boyfriend|"
    r"change\s+my\s+mind|two\s+buttons|galaxy\s+brain|wojak|"
    r"this\s+is\s+fine|gru'?s\s+plan|trade\s+offer)\b",
    re.I,
)
_AI_VISUAL = re.compile(
    r"\b(ai|midjourney|stable\s*diffusion|\bsd\b|sdxl|comfyui|"
    r"flux|generated|aivideo|runway|kling|luma|pika|sora)\b",
    re.I,
)

# Formats GPTunnel showcase cares about → boost early priority
_VISUAL_PRODUCT = re.compile(
    r"\b(meme|face|swap|portrait|template|viral|trend|shorts?|"
    r"reel|tiktok|before\s+after)\b",
    re.I,
)


def classify_trend_type(title: str, subreddit: str = "") -> str:
    text = f"{title} {subreddit}"
    if _FACE_SWAP.search(text):
        return "face-swap"
    if _TEMPLATE.search(text):
        return "template-meme"
    if _AI_VISUAL.search(text) or subreddit.lower() in {
        "aivideo",
        "stablediffusion",
        "midjourney",
        "aiart",
        "singularity",
    }:
        return "ai-visual"
    return "other"


def classify_stage(signals: dict[str, Any], age_hours: float) -> str:
    score = float(signals.get("score") or 0)
    velocity = float(signals.get("upvote_velocity") or 0)

    if age_hours >= PEAK_MIN_AGE_H or score >= HIGH_SCORE:
        return "peak"
    if age_hours < EMERGING_MAX_AGE_H and score < MODERATE_SCORE:
        if velocity >= HIGH_VELOCITY:
            return "rising"
        return "emerging"
    if age_hours < RISING_MAX_AGE_H and (
        velocity >= EARLY_VELOCITY or score >= MODERATE_SCORE // 2
    ):
        return "rising"
    if velocity >= HIGH_VELOCITY:
        return "rising"
    if age_hours < RISING_MAX_AGE_H:
        return "emerging"
    return "peak"


def early_priority_score(
    *,
    stage: str,
    signals: dict[str, Any],
    age_hours: float,
    trend_type: str,
    title: str,
    cluster_size: int,
) -> float:
    """Higher = catch sooner for GPTunnel-style vitrine. Not a contract field name
    required by shared/, stored under signals.early_score (optional key OK).
    """
    velocity = float(signals.get("upvote_velocity") or 0)
    ratio = float(signals.get("upvote_ratio") or 0)
    rank = float(signals.get("rising_rank") or 99)

    stage_w = {"emerging": 100.0, "rising": 70.0, "peak": 10.0}.get(stage, 0.0)
    type_w = {
        "face-swap": 35.0,
        "template-meme": 30.0,
        "ai-visual": 25.0,
        "other": 5.0,
    }.get(trend_type, 0.0)
    freshness = max(0.0, 40.0 - age_hours * 2.5)
    velocity_w = min(velocity, 200.0) * 0.35
    ratio_w = ratio * 15.0
    rank_w = max(0.0, 25.0 - rank * 2.0)
    cluster_w = min(cluster_size, 3) * 8.0
    product_w = 12.0 if _VISUAL_PRODUCT.search(title or "") else 0.0

    return round(
        stage_w + type_w + freshness + velocity_w + ratio_w + rank_w + cluster_w + product_w,
        2,
    )


def is_post_too_old(age_hours: float) -> bool:
    return age_hours > MAX_POST_AGE_H
