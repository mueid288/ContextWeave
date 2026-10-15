"""CLI: emit an example ArtifactFingerprint from a model YAML (no weights)."""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

import yaml

from contextweave.fingerprints.schema import (
    ArtifactFingerprint,
    BuildContextFingerprint,
    ContentIdentity,
    KvLayoutFingerprint,
    ModelFingerprint,
    PositionStorageMode,
    RopeFingerprint,
    TokenizerFingerprint,
    UnknownFieldError,
    hash_build_context,
    hash_token_ids,
)
from contextweave.fingerprints.validate import validate_artifact_fingerprint
from contextweave.tokenization.boundaries import (
    ChunkingConfig,
    canonicalize_segment_tokens,
)


def _rope_type_from_cfg(raw: dict) -> str:
    scaling = raw.get("rope_scaling")
    if scaling is None:
        return "default"
    if isinstance(scaling, dict):
        return str(scaling.get("rope_type") or scaling.get("type") or "llama3")
    return str(scaling)


def _require_int(raw: dict, key: str) -> int:
    val = raw.get(key)
    if val is None:
        raise UnknownFieldError(f"Required model YAML field missing: {key}")
    return int(val)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an example FR-01 fingerprint from configs/models/*.yaml (CPU-only)."
    )
    parser.add_argument(
        "--model-config",
        type=Path,
        default=Path("configs/models/qwen3_8b.yaml"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("benchmarks/reports/example_fingerprint_qwen3.json"),
    )
    parser.add_argument(
        "--allow-unpinned",
        action="store_true",
        default=True,
        help="Allow desk-unpinned revisions for example fingerprints (default on).",
    )
    parser.add_argument(
        "--require-pinned",
        action="store_true",
        help="Reject unpinned revisions (production validation).",
    )
    args = parser.parse_args(argv)
    allow_unpinned = not args.require_pinned

    raw = yaml.safe_load(args.model_config.read_text(encoding="utf-8")) or {}
    try:
        num_layers = _require_int(raw, "num_hidden_layers")
        num_attention_heads = _require_int(raw, "num_attention_heads")
        num_key_value_heads = _require_int(raw, "num_key_value_heads")
        hidden_size = _require_int(raw, "hidden_size")
    except UnknownFieldError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    head_dim = raw.get("head_dim")
    if head_dim is None:
        head_dim = hidden_size // num_attention_heads

    model = ModelFingerprint(
        hf_repo=str(raw.get("hf_repo") or raw.get("name") or "unknown"),
        revision="desk-unpinned",  # replace with real commit on GPU day
        weight_checksum=None,
        architecture=str(raw.get("model_type") or raw.get("attention") or "gqa"),
        num_layers=num_layers,
        num_attention_heads=num_attention_heads,
        num_key_value_heads=num_key_value_heads,
        hidden_size=hidden_size,
        head_dim=int(head_dim),
    )

    scaling = raw.get("rope_scaling")
    if scaling is not None and not isinstance(scaling, dict):
        scaling = {"value": scaling}

    cfg = ChunkingConfig()
    demo_prefix = list(range(10, 42))
    demo_chunk_raw = list(range(1000, 1512))
    demo_chunk = canonicalize_segment_tokens(demo_chunk_raw, cfg, append_boundary=True)

    fp = ArtifactFingerprint(
        model=model,
        tokenizer=TokenizerFingerprint(
            name=str(raw.get("hf_repo") or "unknown") + "-tokenizer",
            revision="desk-unpinned",
            vocab_size=None,
        ),
        rope=RopeFingerprint(
            rope_type=_rope_type_from_cfg(raw),
            rope_theta=float(raw.get("rope_theta") or 10000.0),
            rope_scaling=scaling,
            position_convention="hf-transformers",
            rotation_sign="+",
            feature_pairing="interleaved",
            position_storage_mode=PositionStorageMode.POST_ROPE,
            max_position_embeddings=raw.get("max_position_embeddings"),
        ),
        build_context=BuildContextFingerprint(
            build_context_hash=hash_build_context(
                prefix_token_ids=demo_prefix,
                chunk_token_ids=demo_chunk,
                sink_prefix_token_count=0,
            ),
            canonical=True,
            sink_prefix_token_count=0,
        ),
        content=ContentIdentity(
            document_id="example-doc",
            content_hash="sha256:demo",
            token_ids_hash=hash_token_ids(demo_chunk),
            token_count=len(demo_chunk),
            chunking_config_id="boundary_v1",
            boundary_token_ids=cfg.boundary_token_ids,
            kv_block_size=cfg.kv_block_size,
            padded_to_block=True,
            assembly_rule="boundary_then_pad_concat",
        ),
        kv=KvLayoutFingerprint(
            dtype=str(raw.get("dtype_target") or "bf16"),
            quantization="none",
            layout="research_dense",
            head_dim=int(head_dim),
            num_kv_heads=num_key_value_heads,
            block_size=16,
        ),
        attention_impl="eager_gqa",
        mask_assumptions="causal_full",
        runtime_schema_version="contextweave-r0",
        cache_schema_version="kv-meta-v0",
    )

    result = validate_artifact_fingerprint(fp, allow_unpinned=allow_unpinned)
    digest_str = fp.digest(allow_unpinned=allow_unpinned) if result.ok else None
    payload = {
        "fingerprint_digest": digest_str,
        "validation": result.to_dict(),
        "fingerprint": fp.to_dict(),
        "notes": (
            "Example only. Pin model/tokenizer revisions before any real artifact. "
            "POST_ROPE storage (v2.1 §E). No weights loaded."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"digest": payload["fingerprint_digest"], "validation": result.to_dict()},
            indent=2,
        )
    )
    print(f"Wrote {args.out}")
    return 0 if result.ok else 2


if __name__ == "__main__":
    sys.exit(main())
