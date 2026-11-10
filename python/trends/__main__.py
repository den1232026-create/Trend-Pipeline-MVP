"""CLI: python -m trends refresh"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # repo root = parents[2] from __main__ (trends/__main__.py → python → repo)
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(prog="python -m trends")
    parser.add_argument(
        "command",
        nargs="?",
        default="refresh",
        choices=["refresh", "list"],
        help="refresh writes trends; list prints stored trends",
    )
    args = parser.parse_args(argv)

    from trends import list_trends, refresh

    if args.command == "refresh":
        result = refresh()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("count", 0) >= 1 else 1

    trends = list_trends()
    print(json.dumps({"count": len(trends), "ids": [t["id"] for t in trends]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
