# Plan: Field order A/B (cw-field × CW product)

**Goal:** Decide whether frequency-stable chunk order helps on **live cw-field traffic**, not just the fixed-prompt TTFT suite.

**Already banked (do not re-prove):**
- G0 sim / needle quality / live TTFT **1.79×** on fixed prompts (`Docs/status/closeout-product-v0.md`)
- Provisional field **G0 PASS** (`artifacts/cw-field-g0-2026-10-25-field`) — demand exists; does **not** prove order latency wins

**Question this plan answers:** On real multi-user retrieves from cw-field, does `by_frequency_desc` beat `natural` / BM25 relevance order on (A) prefix-cache share and (B) optional live TTFT — without wrecking answer quality?

---

## Design

| Arm | Order | Where |
|-----|--------|--------|
| A `natural` | BM25 rank as retrieved (no frequency reorder) | cw-field flag or CW replay |
| B `frequency` | Current cw-field prior + `reorder_by_frequency` (after cold start) | default today |
| C `relevance` (optional) | Keep BM25 order only; same as A if no other rerank | — |

**Two layers (run in order):**

### Layer 1 — CPU / free (do first)
Replay banked `partner_v1` → imported trace through `cw-analyze-trace --compare-chunk-order`.

Primary KPIs (from `Docs/product/canonical-order.md`):
- `share_prefix_cached` lift (freq vs natural)
- `post_prefix_prefill_tokens` reduction
- Do **not** use G0 PASS/FAIL as the product score

**Pass heuristic (desk):** freq improves overall `share_prefix_cached` by **≥ +2 pp** vs natural on the field trace, **or** multi-doc subset shows clear lift. Record even if flat/negative.

### Layer 1 result (banked 2026-10-25)

Artifact: `artifacts/product-field-order-ab-2026-10-25/`

- `by_frequency_desc` vs `natural`: **+5.64 pp** prefix share (30.9% → 36.6%), **+8.2%** post-prefix token cut
- Desk bar (≥2 pp): **PASS** · Analyzer pre-reg bar (≥10 pp / 20% cut): **FAIL**

### Decision (2026-10-25)

**Soft-keep frequency as cw-field default. Skip Layer 2.**  
Rationale: positive but sub–pre-reg desk lift; fixed-prompt TTFT already banked;
no need for GPU field TTFT unless a latency claim is required later.
Closeout: `Docs/status/closeout-product-v0.md` (field follow-up section).

### Layer 2 — GPU (only if Layer 1 is non-negative or you need latency truth)
A/B live asks with the same questions/docs:
- Mode off: natural retrieve order → shim/vLLM TTFT
- Mode on: frequency order → TTFT  
Same model/stack as product TTFT suite if possible.

**Pass heuristic (live):** warm p50 TTFT frequency / natural ≥ **1.2×** (weaker than fixed-prompt 1.79× bar; field is noisier). Quality: spot-check or needle-style contains_rate not worse than −10 pp.

---

## Commands

### 0) Bank sync (if not done)

Homeserver: commit/push `artifacts/cw-field-g0-2026-10-25-field`.  
Laptop: `git pull` ContextWeave.

### 1) Layer 1 — compare orders on field trace

```bash
cd "/Users/apple/Code/Context Weave"   # or ~/Mueid/ContextWeave
source .venv/bin/activate

TRACE=artifacts/cw-field-g0-2026-10-25-field/trace.jsonl
OUT=artifacts/product-field-order-ab-2026-10-25
mkdir -p "$OUT"

cw-analyze-trace --trace "$TRACE" \
  --compare-chunk-order \
  --report "$OUT/compare_field.md" \
  --metrics-json "$OUT/compare_field.json"

cat "$OUT/compare_field.md"
```

Write a 5-line `README.md` in `$OUT` with: lift pp, multi-doc lift, pass_heuristic yes/no, claim language.

### 2) Layer 2 — only after Layer 1

**Minimal cw-field change:** env `ORDER_MODE=natural|frequency` (default frequency). Log mode on each ask (already have partner_v1; add `meta.order_mode` if missing).

Then either:
- Colab/vLLM path mirroring `Docs/product/live-shim.md` with field-exported retrieves, or
- Timed asks against the same upstream with mode flipped between sessions

Bank under `artifacts/product-field-order-ttft-YYYY-MM-DD/`.

---

## Success / stop

| Result | Action |
|--------|--------|
| Layer 1 clear C1 lift | Proceed to Layer 2 or soft “integrate order in cw-field by default” |
| Layer 1 flat / negative | **Stop** — keep order optional; do not claim field TTFT wins |
| Layer 2 ≥1.2× warm p50 | Product decide: ship frequency default on field RAG |
| Layer 2 &lt;1.2× or quality drop | Order stays research/default-off for variable retrieve |

---

## Out of scope

- Replacing G0 / growing N for final tokenizer G0
- Changing DeepSeek as the field LLM for Layer 1
- Full multi-tenant production claims

---

## Claim language after this plan

- **If Layer 1+2 pass:** “On live cw-field retrieves, frequency order improved prefix-cache KPIs and warm TTFT vs natural (cite artifact).”
- **If only Layer 1:** “On field traces, frequency order lifts simulated prefix share by X pp; live TTFT not measured.”
- **If fail:** “Field demand (G0) holds; frequency order did not help variable retrieve — fixed-prompt C1 result does not transfer.”
