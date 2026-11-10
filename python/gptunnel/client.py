"""GPTunnel API client — chat (/v1) + CreativeLab media (/api/v2/media)."""

from __future__ import annotations

import base64
import mimetypes
import os
import time
from typing import Any

import httpx

from gptunnel.models import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_IMAGE_MODEL,
    DEFAULT_SCENE_MODEL,
    env_chat_model,
    env_image_model,
    env_scene_model,
    pick_cheapest_chat,
    pick_image_model,
    pick_scene_model,
)


class GPTunnelError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class GPTunnelDownloadError(GPTunnelError):
    """Media task succeeded but CDN bytes could not be pulled locally."""

    def __init__(self, message: str, url: str, status_code: int | None = None):
        super().__init__(message, status_code=status_code)
        self.url = url


class GPTunnelClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        media_base_url: str | None = None,
        timeout: float = 90.0,
    ):
        self.api_key = api_key if api_key is not None else os.getenv("GPTUNNEL_API_KEY", "").strip()
        self.base_url = (
            base_url or os.getenv("GPTUNNEL_BASE_URL", "https://gptunnel.ru/v1")
        ).rstrip("/")
        self.media_base_url = (
            media_base_url
            or os.getenv("GPTUNNEL_MEDIA_BASE_URL", "https://gptunnel.ru/api/v2")
        ).rstrip("/")
        self.timeout = timeout
        self.use_wallet = os.getenv("GPTUNNEL_USE_WALLET", "1").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        # Cached / overridable model ids (health + generate use these).
        self._chat_model = env_chat_model() or DEFAULT_CHAT_MODEL
        self._image_model = env_image_model() or DEFAULT_IMAGE_MODEL
        self._scene_model = env_scene_model() or DEFAULT_SCENE_MODEL
        self._media_schemas: dict[str, dict[str, Any]] = {}
        self._resolved = False

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def image_model(self) -> str:
        return self._image_model

    @property
    def chat_model(self) -> str:
        return self._chat_model

    @property
    def scene_model(self) -> str:
        return self._scene_model

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise GPTunnelError("GPTUNNEL_API_KEY is not set")
        # Docs use Authorization: <API_KEY> (raw key, not always Bearer).
        auth = self.api_key
        if not auth.lower().startswith("bearer "):
            # Keep compatibility: if key looks like OpenAI sk-..., still send raw per GPTunnel docs.
            pass
        return {
            "Authorization": auth,
            "Content-Type": "application/json",
        }

    def _raise_http(self, resp: httpx.Response, kind: str) -> None:
        if resp.status_code in (429, 500, 502, 503, 504):
            raise GPTunnelError(
                f"GPTunnel {kind} temporary error HTTP {resp.status_code}: {resp.text[:300]}",
                status_code=resp.status_code,
            )
        if resp.status_code >= 400:
            raise GPTunnelError(
                f"GPTunnel {kind} error HTTP {resp.status_code}: {resp.text[:400]}",
                status_code=resp.status_code,
            )

    def list_chat_models(self) -> list[dict[str, Any]]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/models", headers=self._headers())
        except httpx.HTTPError as exc:
            raise GPTunnelError(f"GPTunnel models network error: {exc}") from exc
        self._raise_http(resp, "models")
        data = resp.json()
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        if isinstance(data, list):
            return data
        return []

    def list_media_models(self, model_type: str | None = "IMAGE") -> list[dict[str, Any]]:
        params = {}
        if model_type:
            params["type"] = model_type
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    f"{self.media_base_url}/media/models",
                    headers=self._headers(),
                    params=params,
                )
        except httpx.HTTPError as exc:
            raise GPTunnelError(f"GPTunnel media models network error: {exc}") from exc
        self._raise_http(resp, "media models")
        data = resp.json()
        models: list[dict[str, Any]] = []
        if isinstance(data, dict) and isinstance(data.get("models"), list):
            models = data["models"]
        elif isinstance(data, list):
            models = data
        for m in models:
            mid = m.get("id") or m.get("code")
            if isinstance(mid, str):
                self._media_schemas[mid] = m
        return models

    def resolve_models(self) -> dict[str, str]:
        """Pick budget chat/image/scene ids from live catalogs when key is set."""
        chat = self._chat_model or DEFAULT_CHAT_MODEL
        image = self._image_model or DEFAULT_IMAGE_MODEL
        scene = self._scene_model or DEFAULT_SCENE_MODEL
        if self.configured:
            try:
                chat = pick_cheapest_chat(self.list_chat_models()) or chat
            except GPTunnelError:
                pass
            try:
                media = self.list_media_models("IMAGE")
                if not media:
                    media = self.list_media_models(None)
                image = pick_image_model(media) or image
                scene = pick_scene_model(media) or scene
            except GPTunnelError:
                pass
        self._chat_model = chat
        self._image_model = image
        self._scene_model = scene
        self._resolved = True
        return {"chat": chat, "image": image, "scene": scene}

    def pick_budget_image_model(self) -> dict[str, Any] | None:
        """Cheapest IMAGE model meta; prefer faceswap when available."""
        models = self.list_media_models("IMAGE")
        if not models:
            models = self.list_media_models(None)
        if not models:
            return None
        mid = pick_image_model(models) or str(models[0].get("id") or "")
        for m in models:
            if str(m.get("id") or m.get("code")) == mid:
                return m
        return models[0]

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.4,
    ) -> str:
        if not self._resolved and self.configured:
            try:
                self.resolve_models()
            except GPTunnelError:
                pass
        payload: dict[str, Any] = {
            "model": model or self._chat_model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.use_wallet:
            payload["useWalletBalance"] = True
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise GPTunnelError(f"GPTunnel chat network error: {exc}") from exc

        self._raise_http(resp, "chat")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError, TypeError) as exc:
            raise GPTunnelError(f"Unexpected chat response shape: {data!r}") from exc

    @staticmethod
    def _to_data_url(image_bytes: bytes, filename: str = "face.png") -> str:
        mime, _ = mimetypes.guess_type(filename)
        if not mime or not mime.startswith("image/"):
            mime = "image/png"
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{mime};base64,{b64}"

    @staticmethod
    def _pick_input_role(model_meta: dict[str, Any] | None) -> str:
        preferred = ("face", "source", "image", "target", "first_frame", "reference")
        inputs = (model_meta or {}).get("inputs") or []
        roles = []
        for item in inputs:
            if isinstance(item, dict):
                role = item.get("role") or item.get("key")
                if role:
                    roles.append(str(role))
        for pref in preferred:
            for role in roles:
                if role.lower() == pref or pref in role.lower():
                    return role
        return roles[0] if roles else "face"

    def create_media_task(
        self,
        *,
        model: str,
        prompt: str | None = None,
        params: dict[str, Any] | None = None,
        inputs: dict[str, list[str]] | None = None,
        wait: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"model": model, "wait": wait}
        if prompt is not None:
            body["prompt"] = prompt
        if params:
            body["params"] = params
        if inputs:
            body["inputs"] = inputs
        if idempotency_key:
            body["idempotency_key"] = idempotency_key
        if self.use_wallet:
            body["useWalletBalance"] = True
        try:
            with httpx.Client(timeout=max(self.timeout, 120.0)) as client:
                resp = client.post(
                    f"{self.media_base_url}/media/tasks",
                    headers=self._headers(),
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise GPTunnelError(f"GPTunnel media create network error: {exc}") from exc
        self._raise_http(resp, "media create")
        data = resp.json()
        if isinstance(data, dict) and data.get("code") not in (0, None) and "id" not in data:
            raise GPTunnelError(f"GPTunnel media create failed: {data}")
        return data if isinstance(data, dict) else {"raw": data}

    def get_media_task(self, task_id: str) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    f"{self.media_base_url}/media/tasks/{task_id}",
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            raise GPTunnelError(f"GPTunnel media get network error: {exc}") from exc
        self._raise_http(resp, "media get")
        data = resp.json()
        if not isinstance(data, dict):
            raise GPTunnelError(f"Unexpected media task shape: {data!r}")
        return data

    def wait_media_task(
        self,
        task_id: str,
        *,
        poll_seconds: float = 2.0,
        max_wait_seconds: float = 180.0,
    ) -> dict[str, Any]:
        deadline = time.time() + max_wait_seconds
        last: dict[str, Any] = {}
        while time.time() < deadline:
            last = self.get_media_task(task_id)
            status = str(last.get("status") or "")
            if status in ("done", "failed"):
                return last
            time.sleep(poll_seconds)
        raise GPTunnelError(
            f"GPTunnel media task timed out after {max_wait_seconds}s: {task_id} last={last.get('status')}"
        )

    def download_url(self, url: str) -> bytes:
        # On Windows, CDN often fails over IPv6 (hang/timeout) while IPv4 works.
        # Prefer curl -4, then httpx.
        import subprocess
        import tempfile
        from pathlib import Path

        errors: list[str] = []
        tmp = Path(tempfile.gettempdir()) / f"gptunnel_dl_{os.getpid()}.bin"
        try:
            proc = subprocess.run(
                [
                    "curl.exe",
                    "-4",
                    "-fsSL",
                    "--connect-timeout",
                    "20",
                    "--max-time",
                    "120",
                    "-o",
                    str(tmp),
                    url,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0 and tmp.is_file() and tmp.stat().st_size > 0:
                return tmp.read_bytes()
            errors.append(f"curl -4 rc={proc.returncode} {(proc.stderr or '')[:180]}")
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

        try:
            timeout = httpx.Timeout(120.0, connect=20.0)
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(url)
            if resp.status_code >= 400:
                errors.append(f"httpx HTTP {resp.status_code}")
            else:
                return resp.content
        except httpx.HTTPError as exc:
            errors.append(f"httpx={exc}")

        raise GPTunnelError(
            "GPTunnel CDN download failed (try VPN or check IPv6). Details: "
            + " | ".join(errors)
        )

    def result_url_from_task(self, task: dict[str, Any]) -> str:
        results = task.get("result") or []
        if not results:
            raise GPTunnelError(f"GPTunnel media task done but empty result: {task}")
        first = results[0]
        url = first.get("url") if isinstance(first, dict) else None
        if not url:
            raise GPTunnelError(f"GPTunnel media result missing url: {first}")
        return str(url)

    def _finish_media_task(self, task: dict[str, Any]) -> bytes:
        task_id = str(task.get("id") or "")
        status = str(task.get("status") or "")
        if task_id and status not in ("done", "failed"):
            task = self.wait_media_task(task_id)
        status = str(task.get("status") or "")
        if status == "failed":
            err = task.get("error") or task
            raise GPTunnelError(f"GPTunnel media task failed: {err}")
        if status != "done":
            raise GPTunnelError(f"GPTunnel media task not done: status={status} id={task_id}")
        url = self.result_url_from_task(task)
        try:
            return self.download_url(url)
        except GPTunnelError as exc:
            raise GPTunnelDownloadError(
                f"{exc}",
                url=url,
                status_code=getattr(exc, "status_code", None),
            ) from exc

    def _model_meta(self, model_id: str) -> dict[str, Any] | None:
        if model_id in self._media_schemas:
            return self._media_schemas[model_id]
        try:
            for m in self.list_media_models(None):
                if str(m.get("id") or m.get("code")) == model_id:
                    return m
        except GPTunnelError:
            return None
        return None

    def generate_image(
        self,
        prompt: str,
        model: str | None = None,
        params: dict[str, Any] | None = None,
        image_bytes: bytes | None = None,
        filename: str = "face.png",
        image_filename: str | None = None,
        model_meta: dict[str, Any] | None = None,
    ) -> bytes:
        """
        One image scenario via CreativeLab:
        - faceswap: cheap scene generate from prompt, then swap uploaded face onto it
        - other IMAGE: single task with prompt + optional face data-URL input
        """
        if image_filename:
            filename = image_filename
        if not self._resolved and self.configured:
            try:
                self.resolve_models()
            except GPTunnelError:
                pass

        model_id = model or self._image_model
        params = dict(params or {})
        input_role = params.pop("input_role", None)
        scene_model = str(params.pop("scene_model", None) or self._scene_model)
        params.pop("size", None)
        params.pop("strength", None)

        if model_meta is None:
            model_meta = self._model_meta(model_id)

        # --- faceswap path: scene then swap ---
        if model_id == "faceswap":
            if not image_bytes:
                raise GPTunnelError("faceswap requires face image bytes")
            scene_params = {
                k: v for k, v in params.items() if k in ("aspect_ratio", "resolution")
            }
            scene_task = self.create_media_task(
                model=scene_model,
                prompt=prompt,
                params=scene_params or None,
                wait=True,
            )
            scene_bytes = self._finish_media_task(scene_task)
            face_url = self._to_data_url(image_bytes, filename)
            scene_url = self._to_data_url(scene_bytes, "scene.png")
            swap_meta = model_meta or self._model_meta("faceswap") or {}
            roles = []
            for item in swap_meta.get("inputs") or []:
                if isinstance(item, dict):
                    r = item.get("role") or item.get("key")
                    if r:
                        roles.append(str(r))
            # Live schema: source_image + target_image (not bare source/target).
            source_role = next(
                (r for r in roles if "source" in r.lower()),
                "source_image",
            )
            target_role = next(
                (r for r in roles if "target" in r.lower()),
                "target_image",
            )
            # Face → source_image; generated scene → target_image (body/scene).
            inputs = {source_role: [face_url], target_role: [scene_url]}
            swap_task = self.create_media_task(
                model="faceswap",
                prompt=None,
                inputs=inputs,
                wait=True,
            )
            return self._finish_media_task(swap_task)

        # --- generic IMAGE model ---
        inputs: dict[str, list[str]] | None = None
        if image_bytes:
            if not input_role:
                input_role = self._pick_input_role(model_meta)
            data_url = self._to_data_url(image_bytes, filename)
            inputs = {str(input_role): [data_url]}

        prompt_mode = (model_meta or {}).get("prompt")
        send_prompt = None if prompt_mode == "none" else prompt

        task = self.create_media_task(
            model=model_id,
            prompt=send_prompt,
            params=params or None,
            inputs=inputs,
            wait=True,
        )
        return self._finish_media_task(task)


_client: GPTunnelClient | None = None


def get_client() -> GPTunnelClient:
    global _client
    if _client is None:
        _client = GPTunnelClient()
    return _client


def reset_client() -> None:
    """Reload client after .env changes (tests / orchestrator)."""
    global _client
    _client = None
