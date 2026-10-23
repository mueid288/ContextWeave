# Pre-registration: H3 slice-cal GPU confirm (same golds)

**Status:** `VALID` (desk) — waiting on Colab  
**Depends on:** H3 slice-cal LOO **PASS**  
**Not a G2 redo.** Phase 2 / ResolventKV still closed.

## One question

Does a workload-local `(order, fact_type)` table fit on Lisbon/2021/BETA-4242 with
**filler-seed 99** transfer to the **same golds** with **filler-seed 100**
(calibrate → serve within gold distribution; new padding only)?

This is the GPU confirm named in `pre-reg-h3-slice-cal.md` §Next — **not** a new
gold set (that already failed for order-only H3).

## Protocol

1. **Calibrate:** safe cells from `artifacts/h3-confirm-2026-10-23/h3_confirm_trials.jsonl`
   (seed 99, already banked).
2. **Serve (GPU):** collect C0/C3 with `collect_h3_confirm.py --filler-seed 100`
   (same golds, N=12, runs=2).
3. **Eval:** apply seed-99 safe cells → C3 else C0; measure precision / mean_q /
   mean TTFT reduction on the seed-100 JSONL.

## Pass heuristic

| Metric | Bar |
|---|---|
| Precision | ≥ 0.9 |
| Policy mean quality | ≥ 0.95 |
| Mean TTFT reduction vs C0 | ≥ 0.20 |

## Fail ⇒

Slice-cal stays **same-filler / same-session LOO only**; do not claim transfer
across filler text. Keep C3 off unless a fresh local probe builds the table.

## Colab

```bash
colab new -s cw-h3-slice-cal --gpu A100
# … EPIC Path A env as prior H3 confirm …
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
python scripts/phase1/collect_h3_confirm.py \
  --n-requests 12 --runs 2 --filler-seed 100 \
  --out h3_slice_cal_serve.jsonl --json
colab stop -s cw-h3-slice-cal
```

Desk eval after download:

```bash
python scripts/phase1/eval_h3_slice_cal.py \
  --calibrate artifacts/h3-confirm-2026-10-23/h3_confirm_trials.jsonl \
  --serve h3_slice_cal_serve.jsonl \
  --out artifacts/h3-slice-cal-gpu-YYYY-MM-DD/report.json --json
```
