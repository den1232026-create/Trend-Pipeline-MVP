"""Create Job and produce artifact — mock PNG or real GPTunnel media generate."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from gptunnel.client import GPTunnelDownloadError, GPTunnelError, get_client
from PIL import Image, ImageDraw, ImageFont

from . import store


def _new_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"


def _draw_mock_png(
    out_path: Path,
    *,
    job_id: str,
    preset_id: str,
    trend_id: str | None,
) -> None:
    width, height = 768, 1280
    img = Image.new("RGB", (width, height), color=(36, 42, 56))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None

    lines = [
        "MOCK GENERATE",
        f"job: {job_id}",
        f"preset: {preset_id}",
        f"trend: {trend_id or '-'}",
        "watermark: MOCK",
    ]
    y = 80
    for line in lines:
        draw.text((40, y), line, fill=(230, 230, 235), font=font)
        y += 36

    draw.rectangle((0, height - 80, width, height), fill=(200, 60, 60))
    draw.text((40, height - 55), "MOCK", fill=(255, 255, 255), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")


def _run_mock(
    job: dict[str, Any],
    preset: dict[str, Any],
) -> dict[str, Any]:
    job_id = job["id"]
    artifact_name = f"{job_id}.png"
    out_path = store.artifacts_dir() / artifact_name
    _draw_mock_png(
        out_path,
        job_id=job_id,
        preset_id=preset["id"],
        trend_id=preset.get("trend_id"),
    )
    job["status"] = "done"
    job["output_path"] = artifact_name
    job["output_url"] = None
    job["error"] = None
    job["mocked"] = True
    store.write_job(job)
    return job


def _run_real(
    job: dict[str, Any],
    preset: dict[str, Any],
    face_bytes: bytes,
    face_filename: str,
) -> dict[str, Any]:
    client = get_client()
    if not client.configured:
        return _run_mock(job, preset)

    steps = preset.get("steps") or []
    if not steps:
        return _run_mock(job, preset)

    step = steps[0]
    params = dict(step.get("params") or {})
    # Allow scene_model override from preset without sending it as media param.
    scene_override = params.pop("scene_model", None)
    if scene_override:
        client._scene_model = str(scene_override)  # noqa: SLF001 — intentional for this job

    model_id = str(step.get("model") or client.image_model)
    # Legacy stage-1 placeholders are not real CreativeLab ids.
    if model_id.startswith("gptunnel/budget-"):
        model_id = client.image_model
        if "scene_model" not in params and client.scene_model:
            params["scene_model"] = client.scene_model

    try:
        image_bytes = client.generate_image(
            prompt=step.get("prompt") or "",
            model=model_id,
            params=params,
            image_bytes=face_bytes,
            image_filename=face_filename,
        )
    except GPTunnelDownloadError as exc:
        # Generation OK on GPTunnel; only local CDN pull failed (common on Win IPv6).
        # Still mark done + LIVE and let UI load remote URL.
        job["status"] = "done"
        job["output_path"] = None
        job["output_url"] = exc.url
        job["error"] = None
        job["mocked"] = False
        store.write_job(job)
        return job
    except GPTunnelError as exc:
        # Only fall back to mock when MOCK_GENERATE=1.
        # In live mode show the real error in UI instead of a silent MOCK success.
        if store.mock_generate_enabled():
            return _run_mock(job, preset)
        job["status"] = "error"
        job["error"] = str(exc)
        job["output_path"] = None
        job["output_url"] = None
        job["mocked"] = False
        store.write_job(job)
        return job

    job_id = job["id"]
    artifact_name = f"{job_id}.png"
    out_path = store.artifacts_dir() / artifact_name
    out_path.write_bytes(image_bytes)
    job["status"] = "done"
    job["output_path"] = artifact_name
    job["output_url"] = None
    job["error"] = None
    job["mocked"] = False
    store.write_job(job)
    return job


def create_generate_job(
    preset_id: str,
    face_bytes: bytes,
    face_filename: str = "face.png",
) -> dict[str, Any]:
    preset = store.get_preset(preset_id)
    if preset is None:
        raise KeyError(f"preset not found: {preset_id}")

    job_id = _new_job_id()
    input_dir = store.job_input_dir(job_id)
    suffix = Path(face_filename).suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        suffix = ".png"
    face_path = input_dir / f"face{suffix}"
    face_path.write_bytes(face_bytes)

    rel_face = f"data/jobs/{job_id}/face{suffix}"
    use_mock = store.mock_generate_enabled()

    job: dict[str, Any] = {
        "id": job_id,
        "preset_id": preset_id,
        "status": "queued",
        "input_paths": {"face_image": rel_face},
        "output_path": None,
        "error": None,
        "mocked": use_mock,
    }
    store.write_job(job)

    job["status"] = "running"
    store.write_job(job)

    if use_mock:
        return _run_mock(job, preset)
    return _run_real(job, preset, face_bytes, face_filename)
