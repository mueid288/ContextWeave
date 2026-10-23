# Pre-registration: H3 runtime seam key-deviation (EPIC)

**Status:** `VALID` (desk) — waiting on Colab  
**Depends on:** Static H3 (order / slice-cal cross-filler) **FAIL**ed transfer  
**Not a G2 redo.** Phase 2 / ResolventKV still closed.

## One question

Does a **runtime** Layer-0 seam discontinuity score (mean \(1-\cos\) between the
token before each doc chunk and the first LegoLink-N isolated keys of that
chunk, from the EPIC collect pass) predict EPIC/C3 gold-contains fails well
enough that “refuse C3 if score ≥ T else C3” keeps mean contains ≥0.95 and cuts
**mean** TTFT ≥20% vs always-C0 — when **T is fit on filler-seed 99** and
evaluated on **filler-seed 100** (same Lisbon golds)?

In-flight after chunk collect, before LegoLink generate — not a static table.
(Joint prefix+seam re-forward was attempted; it CUDA-IMA’d on EPIC Path A, so
the registered signal is **isolated-seam only**.)

## Why this signal class

| Static (archived for policy) | This pre-reg |
|---|---|
| Order / `(order,fact)` tables | Layer-0 seam keydev scalar |
| Failed cross-gold & cross-filler | Must transfer 99→100 to PASS |

## Protocol

1. **Collect (GPU):** C0 + C3 with `keydev` on each request  
   `scripts/phase1/collect_h3_keydev.py --filler-seed {99,100}`  
   (or one session: seed 99 then 100).
2. **Fit T (CPU):** smallest threshold with train precision ≥0.9 on seed 99  
   (fail-closed if none).
3. **Serve eval:** apply T to seed 100; report precision / mean_q / TTFT red.

## Pass heuristic

| Metric | Bar |
|---|---|
| Seed-100 precision | ≥ 0.9 |
| Policy mean quality | ≥ 0.95 |
| Mean TTFT reduction vs C0 | ≥ 0.20 |

## Fail ⇒

Keep C3 refused by default. Do not reopen static slice-cal fishing. Archive
keydev as inconclusive for this EPIC pin.

## Colab

```bash
colab new -s cw-h3-keydev --gpu A100
# EPIC Path A as prior confirm
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
python scripts/phase1/collect_h3_keydev.py --filler-seed 99 --n-requests 12 \
  --runs 2 --out h3_keydev_seed99.jsonl --json
python scripts/phase1/collect_h3_keydev.py --filler-seed 100 --n-requests 12 \
  --runs 2 --out h3_keydev_seed100.jsonl --json
colab stop -s cw-h3-keydev
```

Desk:

```bash
python scripts/phase1/eval_h3_keydev.py \
  --train h3_keydev_seed99.jsonl --test h3_keydev_seed100.jsonl \
  --out artifacts/h3-keydev-YYYY-MM-DD/report.json --json
```
