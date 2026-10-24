#!/usr/bin/env python3
"""Pull cw-field partner_v1 traces → import → Gate G0 report (CPU-only).

Env (or flags):
  CW_FIELD_URL              default http://127.0.0.1:8787
  CW_FIELD_ADMIN_TOKEN      required for download (or --token / ADMIN_TOKEN)

Examples:
  export CW_FIELD_ADMIN_TOKEN=...
  python scripts/workloads/cw_field_pipeline.py

  python scripts/workloads/cw_field_pipeline.py \\
    --base-url http://127.0.0.1:8787 --token \"$ADMIN_TOKEN\" --tag weekly
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _fetch_traces(base_url: str, token: str, dest: Path) -> int:
    url = f"{base_url.rstrip('/')}/admin/traces?token={urllib.parse.quote(token)}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"download failed HTTP {e.code}: {e.read()[:300]!r}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"download failed: {e}") from e
    text = body.decode("utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def _fetch_health(base_url: str) -> dict:
    url = f"{base_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def _run(cmd: list[str], *, allow_codes: set[int] | None = None) -> int:
    print("+", " ".join(cmd), flush=True)
    code = subprocess.call(cmd, cwd=REPO)
    if code != 0 and (allow_codes is None or code not in allow_codes):
        raise SystemExit(code)
    return code


def _parse_g0_summary(report: Path) -> dict:
    text = report.read_text(encoding="utf-8") if report.is_file() else ""
    out: dict = {"gate": None, "requests": None, "rationale": None}
    m = re.search(r"Gate G0:\s*\*\*(\w+)\*\*", text)
    if m:
        out["gate"] = m.group(1)
    m = re.search(r"Requests:\s*(\d+)", text)
    if m:
        out["requests"] = int(m.group(1))
    m = re.search(r"Rationale:\s*(.+)", text)
    if m:
        out["rationale"] = m.group(1).strip()
    m = re.search(
        r"Recurring non-prefix tokens \(unconstrained\)\s*\|\s*([^\|]+)\|",
        text,
    )
    if m:
        out["recurring_line"] = m.group(1).strip()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("CW_FIELD_URL", "http://127.0.0.1:8787"),
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("CW_FIELD_ADMIN_TOKEN")
        or os.environ.get("ADMIN_TOKEN", ""),
        help="cw-field ADMIN_TOKEN",
    )
    parser.add_argument(
        "--tag",
        default=date.today().isoformat(),
        help="artifact folder suffix (default: today)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse existing raw partner_v1.jsonl in the artifact dir",
    )
    parser.add_argument("--cache-budget-gb", type=float, default=128.0)
    args = parser.parse_args(argv)

    if not args.token and not args.skip_download:
        print(
            "Set CW_FIELD_ADMIN_TOKEN or --token (same as cw-field ADMIN_TOKEN).",
            file=sys.stderr,
        )
        return 2

    art = REPO / "artifacts" / f"cw-field-g0-{args.tag}"
    art.mkdir(parents=True, exist_ok=True)
    raw = art / "partner_v1.jsonl"
    imported = art / "trace.jsonl"
    report = art / "g0_report.md"
    summary_path = art / "summary.json"

    health = _fetch_health(args.base_url)
    print("health:", json.dumps(health, indent=2))

    if args.skip_download:
        if not raw.is_file():
            print(f"missing {raw}", file=sys.stderr)
            return 1
        n = sum(1 for ln in raw.read_text(encoding="utf-8").splitlines() if ln.strip())
        print(f"reusing {n} lines from {raw}")
    else:
        n = _fetch_traces(args.base_url, args.token, raw)
        print(f"downloaded {n} trace lines → {raw}")

    if n < 1:
        print("no traces yet — use cw-field ask first", file=sys.stderr)
        summary_path.write_text(
            json.dumps(
                {
                    "ok": False,
                    "reason": "empty_traces",
                    "health": health,
                    "n_traces": 0,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 1

    _run(
        [
            sys.executable,
            str(REPO / "scripts/workloads/import_trace.py"),
            "--input",
            str(raw),
            "--format",
            "partner_v1",
            "--out",
            str(imported),
        ]
    )
    # analyze_trace exits 2 on G0 FAIL — still bank the report
    _run(
        [
            sys.executable,
            str(REPO / "scripts/workloads/analyze_trace.py"),
            "--trace",
            str(imported),
            "--report",
            str(report),
            "--cache-budget-gb",
            str(args.cache_budget_gb),
        ],
        allow_codes={2},
    )

    g0 = _parse_g0_summary(report)
    summary = {
        "ok": True,
        "base_url": args.base_url,
        "n_traces": n,
        "health": health,
        "g0": g0,
        "paths": {
            "raw": str(raw.relative_to(REPO)),
            "imported": str(imported.relative_to(REPO)),
            "report": str(report.relative_to(REPO)),
        },
        "note": "Provisional until N is large and median chunk / recurrence clear bars.",
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nArtifacts: {art}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
