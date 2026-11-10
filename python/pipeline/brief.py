"""Fill Trend.llm_brief — GPTunnel chat if key present, else heuristic template."""

from __future__ import annotations

from typing import Any

from gptunnel.client import GPTunnelError, get_client

_TYPE_HINTS = {
    "face-swap": (
        "Single budget image step that composites the user face onto the viral character/scene. "
        "Keep one user input: face_image. Emphasize likeness and meme readability."
    ),
    "template-meme": (
        "Template still: place the user face into a classic meme layout matching the trend. "
        "One image step, short punchy caption space if needed."
    ),
    "ai-visual": (
        "Stylized AI still inspired by the trend references; optional light face blend. "
        "Prefer one cheap image model."
    ),
    "other": (
        "Generic image meme still derived from the trend summary; user uploads face_image."
    ),
}


def heuristic_brief(trend: dict[str, Any]) -> str:
    trend_type = trend.get("trend_type") or "other"
    hint = _TYPE_HINTS.get(trend_type, _TYPE_HINTS["other"])
    title = trend.get("title") or "untitled"
    summary = trend.get("summary") or ""
    why = trend.get("why_trending") or ""
    stage = trend.get("stage") or "emerging"
    refs = trend.get("references") or []
    ref_titles = ", ".join(
        (r.get("title") or r.get("url") or "") for r in refs[:3] if isinstance(r, dict)
    )
    return (
        f"Trend '{title}' ({trend_type}, stage={stage}). "
        f"Summary: {summary} "
        f"Why trending: {why} "
        f"Refs: {ref_titles}. "
        f"Pipeline guidance: {hint}"
    ).strip()


def generate_llm_brief(trend: dict[str, Any]) -> str:
    client = get_client()
    if not client.configured:
        return heuristic_brief(trend)

    system = (
        "You write a short pipeline brief for an image meme MVP on GPTunnel. "
        "Return 2-4 sentences: what the format is, why a face_image input fits, "
        "and what a single budget image step should do. No markdown."
    )
    user = (
        f"title: {trend.get('title')}\n"
        f"summary: {trend.get('summary')}\n"
        f"trend_type: {trend.get('trend_type')}\n"
        f"stage: {trend.get('stage')}\n"
        f"why_trending: {trend.get('why_trending')}\n"
        f"references: {trend.get('references')}\n"
    )
    try:
        text = client.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return text or heuristic_brief(trend)
    except GPTunnelError:
        return heuristic_brief(trend)
