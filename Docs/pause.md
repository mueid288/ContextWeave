# Project pause

**Effective:** 2026-10-23  
**State:** **PAUSED** (intentional)  
**Prior decision:** Phase 0 **PIVOT** — [`phase0-exit-decision.md`](phase0-exit-decision.md)

## Why pause

Phase 0’s go/pivot/stop question is answered with measured evidence. Further desk
or GPU work without a new owner decision is busywork. No partner trace is
required to hold this state.

## What is frozen

| Item | Status |
|---|---|
| CacheBlend G1 | CLOSED — do not reopen |
| Phase 1 / G2 / G3 | Not opened |
| ResolventKV kernels | Blocked (§6) |
| Colab / GPU | Idle; no active sessions expected |
| Partner ask | Parked (optional forever) |
| EPIC@12k | Pre-reg only — [`pre-reg-epic-12k.md`](pre-reg-epic-12k.md) |

## What “resume” means

Do **not** “continue Phase 0.” Pick one resume path and write it down first:

1. **Stay paused / archive** — no further research spend.
2. **Run EPIC@12k** — follow the parked pre-reg exactly; then reassess.
3. **Thin planner maintenance** — CPU-only policy/fingerprint tweaks; no GPU.
4. **Open Phase 1** — only after an explicit go memo (not justified by current G1).

## Active artifacts to trust on resume

- `Docs/phase0-exit-decision.md`
- `Docs/g1-closeout-thesis.md`
- `artifacts/g1-diag-2026-10-23/`
- `docs/experiment-log.md` Current verdict
- `contextweave.planner.v0` (refuses C4 under G1 calibration)
