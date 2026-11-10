"""Trend → Preset JSON. Overwrites preset_{trend_id}. Writes llm_brief onto Trend file."""

from __future__ import annotations

from typing import Any

from gptunnel.client import get_client
from gptunnel.models import estimate_preset_cost_rub

from . import store
from .brief import generate_llm_brief
from .trends_bridge import get_trend


def preset_id_for(trend_id: str) -> str:
    return f"preset_{trend_id}"


def _prompt_for(trend: dict[str, Any], llm_brief: str) -> str:
    title = trend.get("title") or "meme"
    summary = trend.get("summary") or ""
    trend_type = trend.get("trend_type") or "other"
    if trend_type == "face-swap":
        base = (
            f"Apply the user face onto the viral format '{title}'. "
            f"Scene: {summary} Vertical meme still, clean face composite, high energy."
        )
    elif trend_type == "template-meme":
        base = (
            f"Place the user face into the meme template for '{title}'. "
            f"Context: {summary} Clear readable still image."
        )
    else:
        base = (
            f"Create an image meme for trend '{title}'. "
            f"Context: {summary} Incorporate the uploaded face naturally."
        )
    return f"{base} Brief: {llm_brief[:280]}"


def _rationale(trend: dict[str, Any], llm_brief: str, image_model: str, scene_model: str) -> str:
    trend_type = trend.get("trend_type") or "other"
    stage = trend.get("stage") or "emerging"
    extra = f" (+ scene via {scene_model})" if image_model == "faceswap" else ""
    return (
        f"trend_type={trend_type}, stage={stage} -> budget image model '{image_model}'{extra}; "
        f"user only uploads face_image. Brief used: {llm_brief[:240]}"
    )


def _resolved_models() -> tuple[str, str, str]:
    client = get_client()
    try:
        resolved = client.resolve_models()
        return resolved["chat"], resolved["image"], resolved["scene"]
    except Exception:  # noqa: BLE001 — presets must still build offline
        return client.chat_model, client.image_model, client.scene_model


def build_preset_from_trend(trend: dict[str, Any]) -> dict[str, Any]:
    llm_brief = generate_llm_brief(trend)
    trend = dict(trend)
    trend["llm_brief"] = llm_brief
    store.write_trend_file(trend)

    _chat, image_model, scene_model = _resolved_models()
    trend_id = trend["id"]
    step_params: dict[str, Any] = {"aspect_ratio": "9:16"}
    if image_model == "faceswap":
        step_params["scene_model"] = scene_model

    preset: dict[str, Any] = {
        "id": preset_id_for(trend_id),
        "trend_id": trend_id,
        "title": f"{trend.get('title', trend_id)} (image MVP)",
        "user_inputs": [
            {"name": "face_image", "type": "image", "required": True},
        ],
        "steps": [
            {
                "model": image_model,
                "prompt": _prompt_for(trend, llm_brief),
                "params": step_params,
            }
        ],
        "output_type": "image",
        "est_cost_rub": estimate_preset_cost_rub(
            image_model, scene_model if image_model == "faceswap" else None
        ),
        "pipeline_rationale": _rationale(trend, llm_brief, image_model, scene_model),
    }
    store.write_preset(preset)
    return preset


def build_preset(trend_id: str) -> dict[str, Any]:
    trend = get_trend(trend_id)
    if trend is None:
        trend = store.get_trend_file(trend_id)
    if trend is None:
        raise KeyError(f"trend not found: {trend_id}")
    return build_preset_from_trend(trend)
