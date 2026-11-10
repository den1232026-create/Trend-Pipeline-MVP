"""
Python HTTP API on localhost:8000 (no /api prefix — Node BFF adds it).
Owns Pipeline routes; Trends routes via import (soft fallback).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure `python/` is on sys.path for `pipeline`, `gptunnel`, `trends`.
_PYTHON_DIR = Path(__file__).resolve().parent
if str(_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(_PYTHON_DIR))

_REPO_ROOT = _PYTHON_DIR.parent
load_dotenv(_REPO_ROOT / ".env")

from pipeline import store  # noqa: E402
from pipeline.build_preset import build_preset  # noqa: E402
from pipeline.generate import create_generate_job  # noqa: E402
from pipeline.trends_bridge import get_trend, list_trends, refresh  # noqa: E402

app = FastAPI(title="trend-meme-pipeline", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    from gptunnel.client import get_client
    from gptunnel.models import DEFAULT_CHAT_MODEL, DEFAULT_IMAGE_MODEL, DEFAULT_SCENE_MODEL

    client = get_client()
    # Do not hit catalogs on every health probe — report defaults / cached ids only.
    models = {
        "chat": getattr(client, "_chat_model", None) or DEFAULT_CHAT_MODEL,
        "image": getattr(client, "_image_model", None) or DEFAULT_IMAGE_MODEL,
        "scene": getattr(client, "_scene_model", None) or DEFAULT_SCENE_MODEL,
    }
    return {
        "ok": True,
        "mock_generate": store.mock_generate_enabled(),
        "gptunnel_configured": client.configured,
        "models": models,
    }


@app.get("/trends")
def http_list_trends() -> list[dict]:
    return list_trends()


@app.get("/trends/{trend_id}")
def http_get_trend(trend_id: str) -> dict:
    trend = get_trend(trend_id)
    if trend is None:
        raise HTTPException(status_code=404, detail=f"trend not found: {trend_id}")
    return trend


@app.post("/trends/refresh")
def http_refresh_trends() -> dict:
    result = refresh()
    if isinstance(result, dict):
        return result
    return {"ok": True, "result": result}


@app.post("/trends/{trend_id}/build-preset")
def http_build_preset(trend_id: str) -> dict:
    try:
        return build_preset(trend_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/presets")
def http_list_presets() -> list[dict]:
    return store.list_presets()


@app.get("/presets/{preset_id}")
def http_get_preset(preset_id: str) -> dict:
    preset = store.get_preset(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail=f"preset not found: {preset_id}")
    return preset


@app.post("/generate")
async def http_generate(
    preset_id: str = Form(...),
    face: UploadFile = File(...),
) -> dict:
    if not preset_id:
        raise HTTPException(status_code=400, detail="preset_id is required")
    face_bytes = await face.read()
    if not face_bytes:
        raise HTTPException(status_code=400, detail="face file is empty")
    try:
        return create_generate_job(
            preset_id=preset_id,
            face_bytes=face_bytes,
            face_filename=face.filename or "face.png",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/jobs/{job_id}")
def http_get_job(job_id: str) -> dict:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    return job


@app.get("/artifacts/{name}")
def http_get_artifact(name: str) -> FileResponse:
    # Prevent path traversal; artifacts are flat files per contracts.
    safe = Path(name).name
    path = store.artifacts_dir() / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"artifact not found: {safe}")
    return FileResponse(path, media_type="image/png")


def main() -> None:
    import uvicorn

    host = os.getenv("PYTHON_HOST", "127.0.0.1")
    port = int(os.getenv("PYTHON_PORT", "8000"))
    uvicorn.run("app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
