#!/usr/bin/env python3
"""Phase 0B baseline entrypoint.

On CPU this lists strategies and exits non-zero for GPU strategies.
On a rented GPU box, replace NotAvailableOnCpu adapters with real runners.
"""

from __future__ import annotations

import argparse
import json
import sys

from contextweave.runtime_adapters.registry import STRATEGIES, get_runner
from contextweave.safety import ModelLoadBlockedError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a Tier-1 baseline. Blocked on laptops by default "
            "(Docs/local-safety.md). GPU rental only."
        )
    )
    parser.add_argument(
        "--strategy",
        choices=STRATEGIES,
        default="smoke",
        help="Baseline strategy (default: smoke)",
    )
    parser.add_argument("--list", action="store_true", help="List strategies and exit")
    parser.add_argument(
        "--prompt",
        default="ContextWeave smoke prompt: document A. Question: what is A?",
        help="Single prompt for smoke / ad-hoc runs",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    args = parser.parse_args(argv)

    if args.list:
        for name in STRATEGIES:
            print(name)
        return 0

    runner = get_runner(args.strategy)
    try:
        runner.setup()
    except (ModelLoadBlockedError, RuntimeError) as exc:
        payload = {
            "strategy": args.strategy,
            "status": "blocked_local",
            "error": str(exc),
            "next": (
                "Do not run models on the laptop. Rent a GPU per Docs/gpu-runbook.md; "
                "set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 only on that host."
            ),
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload["error"])
            print(payload["next"])
        return 1

    from contextweave.runtime_adapters.base import BaselineRequest

    result = runner.run_one(BaselineRequest(request_id="adhoc-0", prompt=args.prompt))
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result)
    runner.teardown()
    return 0 if result.error is None else 2


if __name__ == "__main__":
    sys.exit(main())
