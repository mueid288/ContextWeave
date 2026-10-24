#!/usr/bin/env python3
"""CPU FR fault-injection suite (validation + planner refuses).

  python scripts/phase1/eval_fp_fault_suite.py \\
    --out artifacts/fp-fault-2026-10-24/report.json --json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

_REPO_BOOT = Path(__file__).resolve()
for _cand in _REPO_BOOT.parents:
    if (_cand / "pyproject.toml").exists():
        ROOT = _cand
        break
else:
    raise SystemExit("Could not find repo root (pyproject.toml)")
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from contextweave.fingerprints.schema import (  # noqa: E402
    ArtifactFingerprint,
    BuildContextFingerprint,
    ContentIdentity,
    KvLayoutFingerprint,
    ModelFingerprint,
    PositionStorageMode,
    RopeFingerprint,
    TokenizerFingerprint,
    hash_build_context,
    hash_token_ids,
)
from contextweave.fingerprints.validate import (  # noqa: E402
    fingerprints_compatible,
    validate_artifact_fingerprint,
)
from contextweave.planner.v0 import ConfigId, RequestView, plan  # noqa: E402
from contextweave.provenance.trust import (  # noqa: E402
    ArtifactBuildMode,
    ArtifactLifecycle,
    ProvenanceRecord,
    TrustNamespace,
    TrustNamespaceKind,
)


def _fp(**kwargs) -> ArtifactFingerprint:
    chunk = list(range(16))
    prefix = list(range(8))
    base = ArtifactFingerprint(
        model=ModelFingerprint(
            hf_repo="mistralai/Mistral-7B-Instruct-v0.2",
            revision="abc123",
            weight_checksum=None,
            architecture="llama",
            num_layers=32,
            num_attention_heads=32,
            num_key_value_heads=8,
            hidden_size=4096,
            head_dim=128,
        ),
        tokenizer=TokenizerFingerprint(name="mistral", revision="tok1"),
        rope=RopeFingerprint(
            rope_type="default",
            rope_theta=1_000_000.0,
            rope_scaling=None,
            position_convention="hf-transformers",
            rotation_sign="+",
            feature_pairing="interleaved",
            position_storage_mode=PositionStorageMode.PRE_ROPE,
        ),
        build_context=BuildContextFingerprint(
            build_context_hash=hash_build_context(
                prefix_token_ids=prefix, chunk_token_ids=chunk
            ),
            canonical=True,
            sink_prefix_token_count=0,
        ),
        content=ContentIdentity(
            document_id="d1",
            content_hash="sha256:c",
            token_ids_hash=hash_token_ids(chunk),
            token_count=len(chunk),
            chunking_config_id="test",
            kv_block_size=16,
            padded_to_block=True,
        ),
        kv=KvLayoutFingerprint(
            dtype="bf16",
            quantization="none",
            layout="research_dense",
            head_dim=128,
            num_kv_heads=8,
            block_size=16,
        ),
        attention_impl="eager_gqa",
        mask_assumptions="causal_full",
        runtime_schema_version="r0",
        cache_schema_version="c0",
    )
    for k, v in kwargs.items():
        base = replace(base, **{k: v})
    return base


def _ops() -> TrustNamespace:
    return TrustNamespace("ops", TrustNamespaceKind.OPERATOR)


def _rec(
    *,
    lifecycle: ArtifactLifecycle = ArtifactLifecycle.AVAILABLE,
    ns: TrustNamespace | None = None,
    build_mode: ArtifactBuildMode = ArtifactBuildMode.CANONICAL_ISOLATED,
    build_hash: str = "sha256:ok",
) -> ProvenanceRecord:
    ns = ns or _ops()
    return ProvenanceRecord(
        artifact_id="a1",
        trust_namespace=ns,
        fingerprint_digest="deadbeef",
        build_context_hash=build_hash,
        built_in_canonical_context=True,
        build_mode=build_mode,
        lifecycle=lifecycle,
    )


def _plan_c3(rec: ProvenanceRecord, ns: TrustNamespace) -> ConfigId:
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            keydev_score=0.01,
            keydev_threshold=0.5,
            provenance=rec,
            request_trust=ns,
            request_build_context_hash=rec.build_context_hash,
        )
    )
    return d.chosen


def _cases() -> list[dict]:
    cases: list[dict] = []

    # 1. model mismatch
    a, b = _fp(), _fp(model=replace(_fp().model, hf_repo="other/model"))
    r = fingerprints_compatible(a, b)
    cases.append(
        {
            "fault": "model_mismatch",
            "refused": (not r.ok) and "model_mismatch" in r.reason_codes,
            "detail": r.reason_codes,
        }
    )

    # 2. unsupported RoPE
    bad = replace(_fp(), rope=replace(_fp().rope, rope_type="yarn"))
    r = validate_artifact_fingerprint(bad)
    cases.append(
        {
            "fault": "unsupported_rope_yarn",
            "refused": (not r.ok) and "unsupported_rope_type" in r.reason_codes,
            "detail": r.reason_codes,
        }
    )

    # 3. non-canonical build
    bad = replace(
        _fp(),
        build_context=replace(_fp().build_context, canonical=False),
    )
    r = validate_artifact_fingerprint(bad)
    cases.append(
        {
            "fault": "noncanonical_build",
            "refused": (not r.ok) and "build_context_not_canonical" in r.reason_codes,
            "detail": r.reason_codes,
        }
    )

    # 4. expired lifecycle
    chosen = _plan_c3(_rec(lifecycle=ArtifactLifecycle.EXPIRED), _ops())
    cases.append(
        {
            "fault": "lifecycle_expired",
            "refused": chosen == ConfigId.C0_FULL_PREFILL,
            "detail": [chosen.value],
        }
    )

    # 5. deleted lifecycle
    chosen = _plan_c3(_rec(lifecycle=ArtifactLifecycle.DELETED), _ops())
    cases.append(
        {
            "fault": "lifecycle_deleted",
            "refused": chosen == ConfigId.C0_FULL_PREFILL,
            "detail": [chosen.value],
        }
    )

    # 6. opportunistic harvest
    chosen = _plan_c3(
        _rec(build_mode=ArtifactBuildMode.OPPORTUNISTIC_HARVEST), _ops()
    )
    cases.append(
        {
            "fault": "opportunistic_harvest",
            "refused": chosen == ConfigId.C0_FULL_PREFILL,
            "detail": [chosen.value],
        }
    )

    # 7. cross-namespace trust
    tenant = TrustNamespace("t1", TrustNamespaceKind.TENANT)
    chosen = _plan_c3(_rec(ns=_ops()), tenant)
    cases.append(
        {
            "fault": "cross_namespace_trust",
            "refused": chosen == ConfigId.C0_FULL_PREFILL,
            "detail": [chosen.value],
        }
    )

    # 8. control: happy path must ALLOW C3 (not a refuse case — tracked separately)
    happy = _plan_c3(_rec(), _ops())
    cases.append(
        {
            "fault": "control_allow_c3",
            "refused": happy == ConfigId.C3_EPIC,  # "refused" name overloaded: pass if allowed
            "detail": [happy.value],
            "is_control_allow": True,
        }
    )
    return cases


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    cases = _cases()
    faults = [c for c in cases if not c.get("is_control_allow")]
    control = next(c for c in cases if c.get("is_control_allow"))
    n = len(faults)
    n_ok = sum(1 for c in faults if c["refused"])
    refuse_rate = n_ok / n if n else 0.0
    pass_h = n >= 6 and refuse_rate >= 1.0 and bool(control["refused"])
    payload = {
        "pre_reg": "Docs/pre-reg/pre-reg-fp-fault-suite.md",
        "n_fault_cases": n,
        "refuse_rate": refuse_rate,
        "control_allows_c3": bool(control["refused"]),
        "pass_heuristic": pass_h,
        "cases": cases,
        "note": "Fault cases must refuse; control_allow_c3 must select C3.",
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"refuse_rate={refuse_rate:.3f} control_c3={control['refused']} pass={pass_h}")
    return 0 if pass_h else 4


if __name__ == "__main__":
    raise SystemExit(main())
