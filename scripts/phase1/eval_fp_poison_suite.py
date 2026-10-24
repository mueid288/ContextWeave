#!/usr/bin/env python3
"""CPU HijackKV-style build-context poison suite.

  python scripts/phase1/eval_fp_poison_suite.py \\
    --out artifacts/fp-poison-2026-10-24/report.json --json
"""

from __future__ import annotations

import argparse
import json
import sys
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
from contextweave.fingerprints.validate import fingerprints_compatible  # noqa: E402
from contextweave.planner.v0 import ConfigId, RequestView, plan  # noqa: E402
from contextweave.provenance.trust import (  # noqa: E402
    ArtifactLifecycle,
    ProvenanceRecord,
    TrustNamespace,
    TrustNamespaceKind,
)


def _base_fp(*, prefix: list[int], chunk: list[int]) -> ArtifactFingerprint:
    return ArtifactFingerprint(
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
            document_id="chunk-benign",
            content_hash="sha256:content",
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


def _cases() -> list[dict]:
    chunk = list(range(100, 116))
    victim_prefix = list(range(0, 8))
    out: list[dict] = []
    # Distinct attacker prefixes (injected build contexts).
    for i in range(8):
        attacker_prefix = list(range(1000 + i * 10, 1000 + i * 10 + 8))
        art = _base_fp(prefix=attacker_prefix, chunk=chunk)
        req = _base_fp(prefix=victim_prefix, chunk=chunk)
        # Same content identity; different build policy.
        assert art.content.token_ids_hash == req.content.token_ids_hash
        compat = fingerprints_compatible(art, req)
        refused = (not compat.ok) and (
            "build_context_hash_mismatch" in compat.reason_codes
        )
        # Planner: provenance carries attacker build hash; victim trust ok + keydev
        # would clear — still must not select C3 without matching policy (we bind
        # provenance hash to artifact; quality clear alone is insufficient if we
        # also require fingerprints_compatible in the suite check).
        ns = TrustNamespace("ops", TrustNamespaceKind.OPERATOR)
        rec = ProvenanceRecord(
            artifact_id=f"poison-{i}",
            trust_namespace=ns,
            fingerprint_digest=art.digest() if hasattr(art, "digest") else "x",
            build_context_hash=art.build_context.build_context_hash,
            built_in_canonical_context=True,
            lifecycle=ArtifactLifecycle.AVAILABLE,
        )
        # Planner currently gates on provenance lifecycle/trust, not request
        # build hash. Suite records both: fingerprint refuse + planner decision
        # when quality+provenance look "good".
        victim_hash = req.build_context.build_context_hash
        decision = plan(
            RequestView(
                has_validated_nonprefix_artifacts=True,
                keydev_score=0.01,
                keydev_threshold=0.5,
                provenance=rec,
                request_trust=ns,
                request_build_context_hash=victim_hash,
            )
        )
        planner_refused = decision.chosen == ConfigId.C0_FULL_PREFILL
        out.append(
            {
                "case_id": f"poison_{i:02d}",
                "same_chunk_tokens": True,
                "fingerprint_refused": refused,
                "fingerprint_reasons": list(compat.reason_codes),
                "planner_chosen": decision.chosen.value,
                "planner_refused": planner_refused,
                "pass": refused and planner_refused,
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    cases = _cases()
    n = len(cases)
    n_pass = sum(1 for c in cases if c["pass"])
    refuse_rate = n_pass / n if n else 0.0
    pass_h = n >= 8 and refuse_rate >= 1.0
    payload = {
        "pre_reg": "Docs/pre-reg/pre-reg-fp-poison-suite.md",
        "n_cases": n,
        "refuse_rate": refuse_rate,
        "pass_heuristic": pass_h,
        "cases": cases,
        "note": (
            "Refuse if fingerprints_compatible reports build_context_hash_mismatch "
            "and planner stays on C0 when request_build_context_hash ≠ provenance."
        ),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"refuse_rate={refuse_rate:.3f} pass={pass_h}")
    return 0 if pass_h else 4


if __name__ == "__main__":
    raise SystemExit(main())
