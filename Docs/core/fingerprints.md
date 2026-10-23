# Fingerprints and provenance (FR-01 / FR-02 / FR-04 / FR-13)

CPU-only metadata. **No KV tensors, no model load.**

## Rule

If any validity-critical field is `unknown` / missing → **refuse reuse**.

## Modules

| Module | Role |
|---|---|
| `contextweave.fingerprints.schema` | FR-01/02 dataclasses + digests |
| `contextweave.fingerprints.validate` | FR-04 compatibility checks |
| `contextweave.provenance.trust` | FR-13 namespaces, quarantine, cross-boundary deny |

## Example

```bash
python scripts/workloads/fingerprint_example.py \
  --model-config configs/models/qwen3_8b.yaml \
  --out benchmarks/reports/example_fingerprint_qwen3.json
```

Pin `revision` to a real commit before any GPU artifact is stored.

## Build context (HijackKV) — Mode A only (v2.1)

`BuildContextFingerprint.build_context_hash` covers **build policy** only: prefix tokens +
sink/adapter counts + mask id. Chunk body tokens are **not** in this hash (they live on
`ContentIdentity.token_ids_hash`) so `fingerprints_compatible` can allow cross-chunk reuse
when model/rope/tokenizer/build policy match.  
Non-canonical builds are **always** rejected (Mode A / v2.1 §F). There is no `allowed_noncanonical` bypass.

**Normative:** non-prefix artifacts are created only via **isolated canonical prefills**  
(`ArtifactBuildMode.CANONICAL_ISOLATED`). Mid-prompt opportunistic harvest is illegal  
(`assert_canonical_build_mode`).

## Token assembly (FR-02 / v2.1 / v2.1.1)

Append `boundary_token_ids` to each segment, **then** pad to `kv_block_size`, then concatenate IDs.  
Never `tokenize(text_a + text_b)`. Never insert an unaligned boundary shim between padded blocks.

## Trust

Default deny for cross-namespace reuse. Untrusted namespaces never admit reusable KV artifacts,  
even within the same namespace name. Lifecycle must be `AVAILABLE`.
