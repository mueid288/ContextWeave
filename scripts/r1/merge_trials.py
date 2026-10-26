#!/usr/bin/env python3
"""Merge C3-only trials into a prior C0/C1 JSONL (replace C3 rows by request_id)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True, help="Prior trials (C0/C1/…)")
    p.add_argument("--patch", type=Path, required=True, help="New trials (usually C3)")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    base = _load(args.base)
    patch = _load(args.patch)
    # Drop base rows that share (request_id, config) with patch
    keys = {(r["request_id"], r["config"]) for r in patch}
    kept = [r for r in base if (r["request_id"], r["config"]) not in keys]
    merged = kept + patch
    merged.sort(key=lambda r: (r["request_id"], r["config"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for r in merged:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {args.out} rows={len(merged)} (base={len(base)} patch={len(patch)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
