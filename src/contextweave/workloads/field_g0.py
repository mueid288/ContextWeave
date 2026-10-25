"""Pull cw-field partner_v1 traces → import → Gate G0 report (CPU-only)."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from contextweave.trace_analysis.metrics import (
    DEFAULT_BYTES_PER_TOKEN,
    analyze_trace,
    evaluate_g0,
    render_report,
)
from contextweave.trace_analysis.working_set import WorkingSetConfig
from contextweave.workloads.import_trace import import_trace_file

REPO = Path(__file__).resolve().parents[3]


def _fetch_traces(base_url: str, token: str, dest: Path) -> int:
    url = f"{base_url.rstrip('/')}/admin/traces"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Admin-Token": token,
        },
    )
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


def _fetch_health(base_url: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def _unique_users(raw: Path) -> int:
    users: set[str] = set()
    if not raw.is_file():
        return 0
    for line in raw.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        uid = row.get("user_id")
        if uid:
            users.add(str(uid))
    return len(users)


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
        help="cw-field ADMIN_TOKEN (sent as Authorization Bearer / X-Admin-Token)",
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
    parser.add_argument(
        "--min-traces",
        type=int,
        default=int(os.environ.get("CW_FIELD_MIN_TRACES", "50")),
        help="Refuse to bank below this many traces (default 50; set CW_FIELD_MIN_TRACES=1 for toys)",
    )
    parser.add_argument(
        "--min-users",
        type=int,
        default=int(os.environ.get("CW_FIELD_MIN_USERS", "2")),
        help="Refuse multi-user evidence below this many user_ids (default 2)",
    )
    parser.add_argument(
        "--allow-provisional-ok",
        action="store_true",
        help="Allow summary.ok=true on provisional/synthetic token imports (default: ok=false while provisional)",
    )
    parser.add_argument(
        "--strict-import",
        action="store_true",
        default=True,
        help="Fail if any partner_v1 rows are dropped on import (default on)",
    )
    parser.add_argument(
        "--no-strict-import",
        action="store_false",
        dest="strict_import",
        help="Allow partial imports (legacy)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO,
        help="ContextWeave repo root for artifacts/",
    )
    args = parser.parse_args(argv)

    if not args.token and not args.skip_download:
        print(
            "Set CW_FIELD_ADMIN_TOKEN or --token (same as cw-field ADMIN_TOKEN).",
            file=__import__("sys").stderr,
        )
        return 2

    art = args.repo_root / "artifacts" / f"cw-field-g0-{args.tag}"
    art.mkdir(parents=True, exist_ok=True)
    raw = art / "partner_v1.jsonl"
    imported = art / "trace.jsonl"
    report = art / "g0_report.md"
    metrics_json = art / "g0_metrics.json"
    summary_path = art / "summary.json"

    health = _fetch_health(args.base_url)
    print("health:", json.dumps(health, indent=2))

    if args.skip_download:
        if not raw.is_file():
            print(f"missing {raw}", file=__import__("sys").stderr)
            return 1
        n = sum(1 for ln in raw.read_text(encoding="utf-8").splitlines() if ln.strip())
        print(f"reusing {n} lines from {raw}")
    else:
        n = _fetch_traces(args.base_url, args.token, raw)
        print(f"downloaded {n} trace lines → {raw}")

    n_users = _unique_users(raw)
    if n < args.min_traces:
        summary_path.write_text(
            json.dumps(
                {
                    "ok": False,
                    "reason": "below_min_traces",
                    "n_traces": n,
                    "min_traces": args.min_traces,
                    "n_users": n_users,
                    "health": health,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"below --min-traces ({n} < {args.min_traces})", file=__import__("sys").stderr)
        return 1

    if n_users < args.min_users:
        summary_path.write_text(
            json.dumps(
                {
                    "ok": False,
                    "reason": "below_min_users",
                    "n_traces": n,
                    "n_users": n_users,
                    "min_users": args.min_users,
                    "health": health,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"below --min-users ({n_users} < {args.min_users})", file=__import__("sys").stderr)
        return 1

    try:
        stats = import_trace_file(
            raw, imported, format_name="partner_v1", strict=bool(args.strict_import)
        )
    except Exception as exc:  # noqa: BLE001 — TraceImportError or IO
        summary_path.write_text(
            json.dumps(
                {
                    "ok": False,
                    "reason": "import_strict_failed",
                    "n_traces": n,
                    "error": str(exc),
                    "health": health,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"import failed: {exc}", file=__import__("sys").stderr)
        return 1
    if stats.rows_out < 1:
        summary_path.write_text(
            json.dumps(
                {
                    "ok": False,
                    "reason": "import_empty",
                    "n_traces": n,
                    "import_errors": stats.errors[:20],
                    "health": health,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 1

    if args.cache_budget_gb and args.cache_budget_gb > 0:
        ws_cfg: WorkingSetConfig | None = WorkingSetConfig.from_gb(
            args.cache_budget_gb, DEFAULT_BYTES_PER_TOKEN
        )
    else:
        ws_cfg = None

    metrics = analyze_trace(imported, working_set_cfg=ws_cfg)
    g0 = evaluate_g0(
        metrics,
        provisional=True,
        require_working_set=True,
    )
    report_text = render_report(metrics, g0, trace_path=imported)
    report.write_text(report_text, encoding="utf-8")
    metrics_json.write_text(
        json.dumps(
            {
                "metrics": {
                    k: v
                    for k, v in metrics.to_dict().items()
                    if k not in ("chunk_lengths", "context_lengths", "reuse_distances")
                },
                "g0": g0.to_dict(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    import_meta_path = imported.parent / "import_meta.json"
    provisional = True
    if import_meta_path.is_file():
        try:
            provisional = bool(
                json.loads(import_meta_path.read_text(encoding="utf-8")).get(
                    "provisional_g0", True
                )
            )
        except json.JSONDecodeError:
            provisional = True
    # Bank ok only when G0 passes AND (non-provisional OR explicitly allowed).
    bank_ok = bool(g0.passed) and (not provisional or bool(args.allow_provisional_ok))
    gate = "PASS" if g0.passed else "FAIL"
    summary = {
        "ok": bank_ok,
        "provisional_g0": provisional,
        "base_url": args.base_url,
        "n_traces": n,
        "n_users": n_users,
        "health": health,
        "g0": {
            "gate": gate,
            "passed": bool(g0.passed),
            "requests": metrics.num_requests,
            "rationale": g0.rationale,
            "detail": g0.to_dict(),
        },
        "paths": {
            "raw": str(raw.relative_to(args.repo_root)),
            "imported": str(imported.relative_to(args.repo_root)),
            "report": str(report.relative_to(args.repo_root)),
            "metrics": str(metrics_json.relative_to(args.repo_root)),
        },
        "note": (
            "ok is true only when Gate G0 passes and import is non-provisional "
            "(or --allow-provisional-ok). Synthetic partner_v1 tokens stay provisional."
        ),
    }
    if g0.passed and provisional and not args.allow_provisional_ok:
        summary["reason"] = "provisional_not_bankable"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nArtifacts: {art}")
    if not g0.passed:
        return 2
    if provisional and not args.allow_provisional_ok:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
