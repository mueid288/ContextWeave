"""CLI: live canonical-order shim (CPU).

Examples::

  # Dry-run (no upstream): reorder only
  cw-serve-order --port 8080

  # Forward to a GPU OpenAI server
  CW_UPSTREAM_URL=http://127.0.0.1:8000 cw-serve-order --port 8080

  # One-shot reorder (no server)
  cw-serve-order --reorder-json request.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from contextweave.product.frequency import FrequencyPrior
from contextweave.product.live_order import apply_chat_documents


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument(
        "--upstream",
        default=None,
        help="Upstream OpenAI base URL (sets CW_UPSTREAM_URL)",
    )
    p.add_argument(
        "--mode",
        default=None,
        help="Default cw_chunk_order (sets CW_CHUNK_ORDER)",
    )
    p.add_argument(
        "--cold-start-n",
        type=int,
        default=None,
        help="Observations before frequency mode engages",
    )
    p.add_argument(
        "--reorder-json",
        type=Path,
        default=None,
        help="One-shot: read chat body JSON, print rewritten body, exit",
    )
    args = p.parse_args(argv)

    if args.upstream is not None:
        os.environ["CW_UPSTREAM_URL"] = args.upstream.rstrip("/")
    if args.mode is not None:
        os.environ["CW_CHUNK_ORDER"] = args.mode
    if args.cold_start_n is not None:
        os.environ["CW_COLD_START_N"] = str(args.cold_start_n)

    if args.reorder_json is not None:
        body = json.loads(args.reorder_json.read_text(encoding="utf-8"))
        prior = FrequencyPrior(
            cold_start_n=int(os.environ.get("CW_COLD_START_N", "32"))
        )
        out = apply_chat_documents(
            body,
            prior=prior,
            default_mode=os.environ.get("CW_CHUNK_ORDER", "by_frequency_desc"),
        )
        print(json.dumps(out, indent=2))
        return 0

    from contextweave.product import proxy as proxy_mod

    proxy_mod._reload_runtime_from_env()
    try:
        proxy_mod.serve(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("cw-serve-order stopped", flush=True)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
