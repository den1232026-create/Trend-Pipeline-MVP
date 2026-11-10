"""Budget model defaults + catalog pickers (IDs from GPTunnel docs / live catalogs)."""

from __future__ import annotations

import os
from typing import Any

# Fallbacks when catalogs are unreachable (docs.gptunnel.ru examples / pricing pages).
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_IMAGE_MODEL = "faceswap"
# Cheap text-to-image fallback if faceswap unavailable / needs a target first.
DEFAULT_SCENE_MODEL = "flux-schnell"

# Rough RUB estimates for Preset.est_cost_rub when price catalog missing.
EST_COST_CHAT_RUB = 1
EST_COST_FACESWAP_RUB = 15
EST_COST_SCENE_RUB = 5


def env_chat_model() -> str:
    return (os.getenv("GPTUNNEL_CHAT_MODEL") or DEFAULT_CHAT_MODEL).strip()


def env_image_model() -> str:
    return (os.getenv("GPTUNNEL_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL).strip()


def env_scene_model() -> str:
    return (os.getenv("GPTUNNEL_SCENE_MODEL") or DEFAULT_SCENE_MODEL).strip()


def _cost_context(model: dict[str, Any]) -> float:
    raw = model.get("cost_context")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 9999.0


def pick_cheapest_chat(models: list[dict[str, Any]]) -> str | None:
    """Prefer gpt-4o-mini if present; else lowest cost_context among non-deprecated."""
    alive = [m for m in models if not m.get("deprecated")]
    if not alive:
        return None
    preferred = env_chat_model()
    for m in alive:
        if m.get("id") == preferred:
            return preferred
    for m in alive:
        if m.get("id") == DEFAULT_CHAT_MODEL:
            return DEFAULT_CHAT_MODEL
    alive.sort(key=_cost_context)
    return alive[0].get("id")


def _media_unit_price(model: dict[str, Any]) -> float:
    price = model.get("price")
    try:
        p = float(price)
    except (TypeError, ValueError):
        p = 0.0
    if p > 0:
        return p
    try:
        return float(model.get("price_input") or 9999.0)
    except (TypeError, ValueError):
        return 9999.0


def _has_image_inputs(model: dict[str, Any]) -> bool:
    inputs = model.get("inputs") or []
    return any(
        isinstance(i, dict) and (i.get("kind") == "image" or "image" in str(i.get("formats") or []))
        for i in inputs
    )


def pick_image_model(models: list[dict[str, Any]], prefer_faceswap: bool = True) -> str | None:
    alive = [m for m in models if not m.get("deprecated") and (m.get("type") or "").upper() == "IMAGE"]
    if not alive:
        # Some catalogs omit type or use mixed casing / faceswap as IMAGE-like.
        alive = [m for m in models if not m.get("deprecated")]
    if not alive:
        return None

    preferred = env_image_model()
    ids = {m.get("id") for m in alive}
    if preferred in ids:
        return preferred
    if prefer_faceswap and "faceswap" in ids:
        return "faceswap"

    # Prefer models that accept image inputs (can use uploaded face).
    with_face = [m for m in alive if _has_image_inputs(m)]
    pool = with_face or alive
    pool.sort(key=_media_unit_price)
    return pool[0].get("id")


def pick_scene_model(models: list[dict[str, Any]]) -> str | None:
    """Cheapest prompt-only IMAGE model (for faceswap target generation)."""
    alive = [
        m
        for m in models
        if not m.get("deprecated")
        and (m.get("type") or "").upper() == "IMAGE"
        and m.get("id") != "faceswap"
    ]
    if not alive:
        return env_scene_model()
    preferred = env_scene_model()
    for m in alive:
        if m.get("id") == preferred:
            return preferred
    # Prefer prompt-required / optional without mandatory dual inputs.
    prompt_ok = [
        m
        for m in alive
        if (m.get("prompt") in ("required", "optional"))
        and not any(
            isinstance(i, dict) and i.get("required") and i.get("kind") == "image"
            for i in (m.get("inputs") or [])
        )
    ]
    pool = prompt_ok or alive
    pool.sort(key=_media_unit_price)
    return pool[0].get("id")


def estimate_preset_cost_rub(image_model: str, scene_model: str | None = None) -> float:
    if image_model == "faceswap":
        return float(EST_COST_FACESWAP_RUB + (EST_COST_SCENE_RUB if scene_model else 0))
    return float(EST_COST_SCENE_RUB)
