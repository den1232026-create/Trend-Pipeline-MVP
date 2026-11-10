"""Probe GPTunnel key: list cheap chat + IMAGE models. Does not print the API key."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from gptunnel.client import GPTunnelClient, GPTunnelError  # noqa: E402


def main() -> int:
    key = os.getenv("GPTUNNEL_API_KEY", "").strip()
    if not key:
        print("FAIL: GPTUNNEL_API_KEY empty in .env — paste key and save (Ctrl+S)")
        return 1

    client = GPTunnelClient()
    print(f"OK: key present (len={len(key)})")
    print(f"chat_base={client.base_url}")
    print(f"media_base={client.media_base_url}")

    try:
        chat_models = client.list_chat_models()
        print(f"chat_models={len(chat_models)}")
        cheap = sorted(
            chat_models,
            key=lambda m: float(m.get("cost_completion") or 999),
        )[:5]
        for m in cheap:
            print(
                f"  chat {m.get('id')} cost_ctx={m.get('cost_context')} "
                f"cost_out={m.get('cost_completion')}"
            )
    except GPTunnelError as exc:
        print(f"chat models ERROR: {exc}")

    try:
        media = client.list_media_models("IMAGE")
        if not media:
            media = client.list_media_models(None)
        print(f"media_models={len(media)}")
        picked = client.pick_budget_image_model()
        if picked:
            print(
                f"  pick id={picked.get('id')} type={picked.get('type')} "
                f"price={picked.get('price')} prompt={picked.get('prompt')}"
            )
            inputs = picked.get("inputs") or []
            for inp in inputs[:6]:
                print(f"    input role={inp.get('role') or inp.get('key')} kind={inp.get('kind')}")
        # Show cheapest 8 IMAGE-ish
        def pkey(m: dict) -> float:
            p = m.get("price")
            if isinstance(p, (int, float)) and p > 0:
                return float(p)
            return float(m.get("price_input") or 9999)

        for m in sorted(media, key=pkey)[:8]:
            print(f"  media {m.get('id')} type={m.get('type')} price={m.get('price')}")
    except GPTunnelError as exc:
        print(f"media models ERROR: {exc}")

    try:
        text = client.chat(
            messages=[{"role": "user", "content": "Reply with exactly: pong"}],
            model=os.getenv("GPTUNNEL_CHAT_MODEL", "gpt-4o-mini"),
        )
        print(f"chat_smoke={text[:80]!r}")
    except GPTunnelError as exc:
        print(f"chat smoke ERROR: {exc}")

    print("Set GPTUNNEL_IMAGE_MODEL / GPTUNNEL_CHAT_MODEL in .env from the pick above.")
    print("Then MOCK_GENERATE=0 for real generate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
