"""CLI: demo shipped planner policy (CPU-only, no model load).

Shows C1 / C0 / refused-C3 paths after Phase 0/1 closeout.
"""

from __future__ import annotations

import argparse
import json
import sys

from contextweave.planner.v0 import plan, RequestView
from contextweave.provenance.trust import (
    ArtifactLifecycle,
    ProvenanceRecord,
    TrustNamespace,
    TrustNamespaceKind,
)


def _ops() -> TrustNamespace:
    return TrustNamespace("ops", TrustNamespaceKind.OPERATOR)


def _available() -> ProvenanceRecord:
    return ProvenanceRecord(
        artifact_id="demo-a1",
        trust_namespace=_ops(),
        fingerprint_digest="demo",
        build_context_hash="sha256:demo-prefix",
        built_in_canonical_context=True,
        lifecycle=ArtifactLifecycle.AVAILABLE,
    )


def _scenarios() -> list[tuple[str, RequestView]]:
    rec = _available()
    ns = _ops()
    return [
        (
            "exact_prefix",
            RequestView(has_exact_prefix=True),
        ),
        (
            "no_reuse_signals",
            RequestView(has_validated_nonprefix_artifacts=False),
        ),
        (
            "c3_blocked_no_provenance",
            RequestView(
                has_validated_nonprefix_artifacts=True,
                keydev_score=0.01,
                keydev_threshold=0.5,
            ),
        ),
        (
            "c3_blocked_build_hash_mismatch",
            RequestView(
                has_validated_nonprefix_artifacts=True,
                keydev_score=0.01,
                keydev_threshold=0.5,
                provenance=rec,
                request_trust=ns,
                request_build_context_hash="sha256:other-prefix",
            ),
        ),
        (
            "c3_allowed_demo_only",
            RequestView(
                has_validated_nonprefix_artifacts=True,
                keydev_score=0.01,
                keydev_threshold=0.5,
                provenance=rec,
                request_trust=ns,
                request_build_context_hash=rec.build_context_hash,
            ),
        ),
        # Product path: canonicalize chunk order upstream → more exact-prefix C1;
        # without that, shuffled multi-doc looks like no reuse → C0.
        (
            "canonical_order_enables_prefix_c1",
            RequestView(has_exact_prefix=True),
        ),
        (
            "shuffled_order_falls_back_c0",
            RequestView(has_exact_prefix=False, has_validated_nonprefix_artifacts=False),
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--scenario",
        choices=[s for s, _ in _scenarios()] + ["all"],
        default="all",
    )
    args = p.parse_args(argv)

    rows = []
    for name, view in _scenarios():
        if args.scenario != "all" and name != args.scenario:
            continue
        d = plan(view)
        rows.append({"scenario": name, **d.to_dict()})

    payload = {
        "closeout": "Docs/status/closeout-phase0-1.md",
        "product": "Docs/product/canonical-order.md",
        "policy": (
            "C1 if prefix else C0; C3 only with provenance+build-hash+quality clear; "
            "prefer by_frequency_desc chunk order upstream to amplify C1"
        ),
        "scenarios": rows,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(payload["policy"])
        for row in rows:
            print(f"  {row['scenario']}: chosen={row['chosen']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
