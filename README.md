# ContextWeave

**Product (v0.2):** Canonical Order **C1** evaluation kit — reorder retrieved RAG
chunks so shared documents form a stable prefix, raising native **prefix-cache**
hits on multi-query workloads.

| Start | Link |
|---|---|
| Claims (can / cannot) | [Docs/product/CLAIMS.md](Docs/product/CLAIMS.md) |
| Readiness | [Docs/product/READINESS.md](Docs/product/READINESS.md) |
| Integrator guide | [Docs/product/integrators.md](Docs/product/integrators.md) |
| Live shim | [Docs/product/live-shim.md](Docs/product/live-shim.md) |
| Field dogfood (cw-field) | [Docs/product/cw-field-kit-dogfood.md](Docs/product/cw-field-kit-dogfood.md) |
| Ship note | [Docs/status/ship-v0.2-c1-kit.md](Docs/status/ship-v0.2-c1-kit.md) |
| Control plane (north star) | [Docs/product/control-plane-north-star.md](Docs/product/control-plane-north-star.md) |
| Gate R1 harness | [Docs/plans/2026-10-26-r1-oracle-harness.md](Docs/plans/2026-10-26-r1-oracle-harness.md) |

**Not** a multi-tenant SaaS · **Not** cw-field itself.  
**Approved direction:** fail-closed reuse control plane (R1 open). Phase 0/1
evidence stays archived ([Docs/status/ARCHIVE.md](Docs/status/ARCHIVE.md)).

**Laptop policy:** never download or run models here —
[Docs/runbooks/local-safety.md](Docs/runbooks/local-safety.md).

## Quick start — C1 kit (CPU)

```bash
git checkout main
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Library
python -c "
from contextweave.product import FrequencyPrior, reorder_documents
prior = FrequencyPrior(cold_start_n=0)
print(reorder_documents(
    [{'document_id': 'b', 'content': 'B'}, {'document_id': 'a', 'content': 'A'}],
    'by_frequency_desc', prior=prior))
"

# Measure order A/B (regenerate trace first if missing)
cw-generate-workload --config configs/workloads/synthetic_rag_default.yaml
cw-analyze-trace --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --compare-chunk-order --report /tmp/compare_chunk_order.md

# OpenAI-compatible reorder shim
cw-serve-order --reorder-json /path/to/req.json --cold-start-n 0
# Dry-run chat completions need: CW_ALLOW_DRY_RUN=1
# With GPU upstream: CW_UPSTREAM_URL=http://gpu:8000 cw-serve-order --port 8080
```

## Field dogfood

Pull live `partner_v1` from [cw-field](https://github.com/mueid288/cw-field-traffic-app),
import, Gate G0 (provisional on synthetic tokens):

```bash
export CW_FIELD_URL=http://127.0.0.1:8787 CW_FIELD_ADMIN_TOKEN=…
cw-field-g0 --allow-provisional-ok   # local; omit allow for bankable ok=false
```

Trace format: [Docs/product/trace-schema.md](Docs/product/trace-schema.md).

## Layout

```text
src/contextweave/product/   C1 library + live shim
src/contextweave/oracle/    Gate R1 CPU upside (no model load)
src/contextweave/trace_analysis/  metrics + chunk-order compare
src/contextweave/workloads/ import, field_g0, synthetic/corpus
Docs/product/               CLAIMS, integrators, dogfood, north star
Docs/plans/                 Thesis + R1 harness
artifacts/                  Banked claim evidence only
scripts/workloads/          G0 + field pipeline wrappers
scripts/product/            Claim reproduction evals
scripts/r1/                 GPU collect notes (collector TBD)
```

## Gates (honest)

- **Product C1:** scoped COMPLETE — see CLAIMS + READINESS.
- **Field G0:** provisional PASS banked (`artifacts/cw-field-g0-2026-10-25-field/`).
- **Control plane:** thesis approved; Gate R1 open (CPU `cw-r1-oracle`; GPU collect pending).
- **Research G1/G2 / EPIC:** archived negative evidence — do not reuse as R1 proof.
