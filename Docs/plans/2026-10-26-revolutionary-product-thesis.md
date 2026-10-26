# Plan — Revolutionize ContextWeave (PRD-aligned product thesis)

**Date:** 2026-10-26  
**Status:** **Approved** (2026-10-26) — execute R0 → R1; control plane only if R1 passes  
**Supersedes for direction:** C1-only outbound as the *end state* (C1 remains a useful *component*)  
**Archive policy:** This document is the written thesis required by [`Docs/status/ARCHIVE.md`](../status/ARCHIVE.md) to reopen planner / PIC work.  
**Primary workload:** enterprise multi-doc RAG (cw-field dogfood); multi-agent deferred.  
**Gate R1 numbers:** ratified as written in §5 (edit only before viewing R1 data).

---

## 0. Verdict

**C1 (frequency reorder) is useful and shippable. It is not the PRD product, and it will not “change AI.”**

The PRD’s unique product is already stated:

> *A validity-checked, quality-gated planner for self-hosted LLM serving that chooses among prefix reuse, non-prefix reuse/repair, and full prefill — and refuses reuse when validity cannot be established.*

That is still the only differentiation that survives 2026 prior art. Repair algorithms are crowded (CacheBlend, SpecCache, FusionRAG, Cache-Craft, …). Ordering is crowded (CacheWeaver, CRAFT, RAGCache trees). Infra is crowded (LMCache, Mooncake, vLLM/SGLang radix). **What remains open — and what engines are explicitly leaving to a “provider” — is the fail-closed decision + quality contract layer.**

---

## 1. What the PRD actually requires (uniqueness bar)

| PRD element | Meaning | C1 kit today |
|---|---|---|
| Validity-checked | Fingerprints: model, tokenizer, RoPE, KV layout, **build-context**, trust namespace | Missing |
| Quality-gated | Calibrated risk records; refuse when quality margin unknown | Missing |
| Planner | Per-request choose C0 / prefix / order / blend-or-repair | Fixed frequency heuristic |
| Refuse unsafe reuse | Observable fallback with reason codes | Always “reorder or not” |
| Training-free MVP | Frozen weights | Yes (accidental) |
| Change the serving contract | Operators get a **quality SLO on reuse**, not just faster TTFT | Showcase demo only |

**Value prop to test (PRD §3.5, still binding):**

> If you self-host a model and repeatedly send the same long reference material in varying positions, ContextWeave picks, per request, the cheapest reuse strategy that stays inside your quality margin, and falls back to full prefill when it cannot show that reuse is valid.

That is the “change AI” bar: **reuse becomes a first-class, auditable serving policy**, not a silent cache optimization.

---

## 2. Research landscape (2026) — what is already taken

### Owned / commoditizing

| Layer | Who | Implication for us |
|---|---|---|
| Exact prefix cache | vLLM, SGLang | Baseline, not a product |
| Distributed KV store / offload | Mooncake, LMCache backends | Do not rebuild |
| Selective recompute blend | CacheBlend inside LMCache; SpecCache; FusionRAG | Do not invent another blend |
| Cache-aware ordering | CacheWeaver, CRAFT, RAGCache | C1 is a thin peer, not a moat |
| Learned PIC | KVLink, ATTUNER, SemPIC, … | Out of MVP (PRD §3.3) |

### Still open (white space)

1. **Semantic / non-prefix reuse *provider*** — vLLM RFC [#44223](https://github.com/vllm-project/vllm/issues/44223) and TensorRT-LLM [#14918](https://github.com/NVIDIA/TensorRT-LLM/issues/14918) keep engines exact-cache-safe and push **quality policy, donor discovery, fail-closed fallback, namespace isolation** to an external provider. Nobody owns a production-grade, open, training-free provider with calibrated refuse rates.
2. **Cross-method selection** — Independent CLC study (arXiv 2603.20218): methods are complementary; no fixed config wins. PRD H2. Our G2 oracle work already showed **speed ≠ quality**; that failure is *evidence for a planner*, not evidence against the thesis — if interpreted as “always blend” fails.
3. **Provenance / HijackKV-class safety** — Build-context poisoning remains a real failure mode papers acknowledge; commercial caches underspecify it.
4. **Multi-agent / multi-source assembly** — KVShareArena: position fix alone fails when questions need several sources; repair or refuse is mandatory. Agent workloads are the growth surface beyond classic RAG.

### What our negative results actually say

| Result | Wrong conclusion | Right conclusion |
|---|---|---|
| CacheBlend harness closed / quality loss | “PIC is dead” | Un-gated blend is unsafe → **need a gate** |
| G2: C3 faster, quality 0.70 vs C0 1.0 | “Planner useless” | Fixed C3 loses; planner must **prefer C0** when risk high (that *is* the product) |
| C1 ~20–33% TTFT peers | “We won” | Incremental; peers exist; **component only** |

---

## 3. Locked product thesis (choose this)

### Name (working)

**ContextWeave Control Plane** — *fail-closed reuse policy for self-hosted LLM serving.*

### One-sentence uniqueness

**We do not invent the cache; we decide, prove, and refuse.** ContextWeave is the layer that turns LMCache / prefix / order / blend into a **quality-bounded policy** with fingerprints, calibration, and observable fallback — the piece engines say they will not own.

### Product shape (v1)

```text
App / RAG / Agent
        │
        ▼
┌───────────────────────────────┐
│  ContextWeave Control Plane   │  ← OUR PRODUCT
│  plan(request) →              │
│    fingerprints + trust ns    │
│    cost model (H4)            │
│    quality-risk gate (H3)     │
│    choose: C0 | C1-order |    │
│            prefix | blend     │
│    else REFUSE → full prefill │
└───────────────┬───────────────┘
                │ policy + donor plan
                ▼
     vLLM / SGLang + LMCache     ← THEIR PLUMBING
```

### Configuration set (reuse existing methods — PRD §7.6)

| Code | Strategy | Role |
|---|---|---|
| C0 | Full prefill | Safe default |
| C1 | Canonical / cache-aware order + native prefix | Shipped kit; warm path when docs recur |
| C2 | Exact prefix only (no reorder) | Baseline |
| C3 | LMCache CacheBlend / equivalent (bounded recompute %) | Non-prefix when calibrated safe |
| C4 | Refuse + metric | Always available |

**v1 does not ship a new repair kernel.** ResolventKV / SAFE-KV-style spectral repair stays **blocked** until a gated C3 path shows a quality-preserving win (existing ResolventKV adoption rule).

### Moat (honest)

| Durable | Fragile |
|---|---|
| Calibration + fingerprint schema + refuse semantics + eval harness | Heuristic reorder alone |
| Workload-slice quality records (FR-14) | “1.5× TTFT” marketing |
| Plugin / provider API above engines | Forking vLLM |
| Design-partner traces + published fault suites | Paper-only novelty |

Platform absorption (PRD §3.4) remains the #1 risk → **build as provider/plugin**, keep eval publishable, accept upstream contribution as exit.

---

## 4. Explicit non-goals (to stay unique)

- Do **not** market C1 as the revolutionary product.
- Do **not** build another CacheBlend / SpecCache / FusionRAG.
- Do **not** rebuild Mooncake / LMCache storage.
- Do **not** train adapters for MVP.
- Do **not** claim universal TTFT wins on unique single-shot prompts.
- Do **not** reopen ResolventKV kernels without a separate go decision after Gate R1 below.

---

## 5. Phased plan (gates before code sprawl)

### Phase R0 — Decision & honesty (3–5 days, docs only)

**Deliverables**

1. Approve this thesis (or reject and stay C1-lab-only).
2. Update [`ARCHIVE.md`](../status/ARCHIVE.md) / [`gaps.md`](../status/gaps.md): planner reopen allowed under this plan only.
3. Rewrite product north star in [`CLAIMS.md`](../product/CLAIMS.md) draft section “Future claims (not shippable)” — keep C1 claims honest.
4. Pick first design-partner workload class: **enterprise multi-doc RAG** *or* **multi-agent report assembly** (prefer RAG if cw-field is the dogfood; agent if aiming harder at “change AI”).

**Exit:** Written go / stay-C1 / stop.

### Phase R1 — Falsify H2 cheaply (1–2 GPU-weeks)

**Question:** On a fixed model + runtime pin, does **oracle** per-request choice among {C0, C1-order+prefix, C3-blend@r%} beat the best *fixed* arm on the **quality/latency frontier** after counting planner overhead?

**Harness (reuse archived Phase 1 ideas, new bank)**

- Model: Qwen2.5/3-8B or Mistral-7B (one pin).
- Runtime: vLLM + prefix; LMCache CacheBlend for C3.
- Workload: HotpotQA / 2Wiki multi-hop + Zipfian doc recurrence (not needle-only).
- Metrics: answer preservation vs C0; TTFT p50/p95; refuse rate; **zero invalid fingerprint reuse** (fault inject).

**Gate R1 (proposed)**

| Pass if | Fail if |
|---|---|
| Oracle upside ≥ **+10% p95 TTFT** at quality within **−2 pp** of C0 *or* equal TTFT with **+2 pp** quality vs best fixed | Upside < threshold after overhead |
| At least one slice where fixed C3 fails quality but C0/C1 passes (proves need for gate) | All arms equivalent → no planner value |

**On fail:** Stay C1 kit + optional order-only product; do not build control plane.  
**On pass:** Proceed R2.

### Phase R2 — Risk signal + fingerprints (2–3 weeks)

Implement the **minimum control plane** as a library + sidecar API (not SaaS):

| Module | PRD FR | MVP behavior |
|---|---|---|
| Fingerprint | FR-01/04 | Hash model+tokenizer+RoPE+KV layout+build-context; mismatch → C0 |
| Trust namespace | FR-13 | Tenant/salt isolation; cross-ns refuse |
| Plan API | FR-06 | `POST /v1/cache/plan` → strategy + reason |
| Calibration store | FR-14 | Per-slice measured quality deltas; expire on fingerprint change |
| Risk gate H3 | — | Start rule-based: multi-hop synthesis + high cross-chunk dependence → prefer C0/C1; low-risk lookup → allow C3 |
| Cost model H4 | — | Break-even vs measured TTFT; error band target ±20% |
| Fallback | FR-08 | Always C0 with reason code |

**Gate R2:** Fault suite (poisoned build-context, wrong model rev, stale donor) → **0 silent invalid reuses**; planner vs best fixed meets R1 bar with *online* (non-oracle) policy within 50% of oracle upside.

### Phase R3 — Engine provider integration (3–4 weeks)

- Ship as **vLLM semantic-reuse provider** (discovery-only mode first, then materialize) and/or LMCache policy hook.
- cw-field becomes a **control-plane dogfood**: dual boards show *plan reason* (C0 vs C1 vs C3), not only natural vs frequency.
- Layer 2 live TTFT + quality banked on field-like traffic.

**Gate R3 (product-shaped):** Design partner can set `quality_margin` and see refuse rate + TTFT; “invalid reuse = 0” in chaos week.

### Phase R4 — Optional mechanism leap (only if R1–R3 pass and gap remains)

Revisit ResolventKV / SAFE-KV-class repair **as one more strategy in the set**, not as the company identity. Same refuse-first contract. 72h diagnostic before kernels (existing ResolventKV adoption rule).

---

## 6. How this “changes AI” (non-hype version)

Today’s AI stack treats context as **stateless text** and cache as **best-effort speedup**. Wrong reuse silently corrupts answers; right reuse is invisible.

ContextWeave’s revolution is contractual:

1. **Context becomes versioned, fingerprintable memory** (not just prompt bytes).
2. **Reuse is policy**, with quality margins and refuse — like typed memory, not a cache hit rate dashboard.
3. **Agents and RAG stop paying full prefill for every reordering** *without* gambling answer quality.

That is a serving-contract change, not a model-IQ change — and it is the only change the PRD asked for.

---

## 7. Relationship to current repos

| Asset | Role under this plan |
|---|---|
| `contextweave` C1 kit | **Strategy C1** inside the planner; keep shipping; do not oversell |
| cw-field showcase | Dogfood → evolve to show **plan decisions + refuse reasons** |
| Archived Phase 0/1 | Evidence bank + negative results; reopen only under R1 harness |
| CLAIMS.md | C1 claims stay; add “Control Plane — not claimed yet” |

Near-term C1 hygiene (M1–M3 in gaps.md) remains optional and **orthogonal**; it does not substitute for R0–R3.

---

## 8. Effort & risk snapshot

| Path | Effort | Upside | Risk |
|---|---|---|---|
| Stay C1-only | Low | Lab kit, incremental TTFT | Not unique; peers win on paper |
| **Control plane (this plan)** | Med–High | PRD-aligned; engine RFCs want it | Platform absorption; need real workload |
| ResolventKV-first | Very High | Possible mechanism leap | Blocked by our own rules; unproven math |

**Recommendation:** Approve **R0 → R1**. Build the control plane only if R1 passes. Keep C1 as the first strategy in the set.

---

## 9. Approval checklist

- [x] Approve thesis: *fail-closed reuse control plane* as the product
- [x] Choose primary workload: **enterprise multi-doc RAG** (multi-agent deferred)
- [x] Ratify Gate R1 numbers (as written in §5; do not edit after seeing data)
- [x] Authorize archive reopen for planner/PIC **under this plan only**
- [x] Defer ResolventKV kernels until post-R3 gap review

**In progress:** R0 docs → R1 oracle harness (see [`2026-10-26-r1-oracle-harness.md`](2026-10-26-r1-oracle-harness.md)).
