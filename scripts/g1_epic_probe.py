#!/usr/bin/env python3
"""G1 EPIC pin probe — detect DerekHJH/epic (vLLM fork) vs stock vLLM.

Does **not** load a model. Safe to run on the current Colab pin to bank a
documented BLOCKED result when stock vLLM 0.32 is installed.

  python scripts/g1_epic_probe.py --json | tee g1_epic_probe.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _scan_vllm_tree(root: Path) -> dict:
    """Look for EPIC fork markers (cache_fuse / hack_kv / kvlink)."""
    markers = ("cache_fuse_metadata", "hack_kv", "kvlink")
    hits: dict[str, list[str]] = {m: [] for m in markers}
    # Cap walk — installed trees are large.
    checked = 0
    for path in root.rglob("*.py"):
        checked += 1
        if checked > 4000:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in markers:
            if m in text and len(hits[m]) < 5:
                hits[m].append(str(path.relative_to(root)))
    return {
        "files_scanned": checked,
        "marker_hits": {k: v for k, v in hits.items() if v},
        "has_cache_fuse": bool(hits["cache_fuse_metadata"]),
        "has_hack_kv": bool(hits["hack_kv"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload: dict = {
        "gate": "G1-step4-epic-probe",
        "epic_fork_detected": False,
        "pass_heuristic": False,
        "note": "",
    }

    try:
        import vllm
    except ImportError as exc:
        payload["error"] = f"vllm not importable: {exc}"
        payload["note"] = (
            "No vLLM in this env. EPIC needs DerekHJH/epic (vLLM ~0.7 fork) "
            "in a dedicated GPU session — see Docs/g1-epic.md."
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload["note"])
        return 2

    vllm_file = Path(vllm.__file__).resolve()
    root = vllm_file.parent
    version = getattr(vllm, "__version__", "unknown")
    scan = _scan_vllm_tree(root)
    fork_ok = scan["has_cache_fuse"] and scan["has_hack_kv"]

    payload.update(
        {
            "vllm_version": version,
            "vllm_path": str(root),
            "scan": scan,
            "epic_fork_detected": fork_ok,
            "pass_heuristic": fork_ok,
            "note": (
                "EPIC fork markers found — run scripts/g1_epic_bench.py next."
                if fork_ok
                else (
                    "Stock vLLM (no cache_fuse_metadata / hack_kv). "
                    "DerekHJH/epic is a vLLM ~0.7 fork (torch==2.5.1 build), "
                    "not a plugin for vLLM 0.32. Documented pin BLOCK for this "
                    "Colab stack; use Docs/g1-epic.md for a dedicated reinstall."
                )
            ),
        }
    )

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"epic_fork={fork_ok} vllm={version} "
            f"cache_fuse={scan['has_cache_fuse']} hack_kv={scan['has_hack_kv']}"
        )
        print(payload["note"])

    # Exit 0 if fork present; 3 = documented pin block (expected on Colab 0.32).
    return 0 if fork_ok else 3


if __name__ == "__main__":
    sys.exit(main())
