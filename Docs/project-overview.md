# ContextWeave — Project Overview

**What this file is:** a plain-language map of the whole project.  
**Who it is for:** anyone who wants the idea in simple words, and anyone who wants the technical picture without reading the full PRD.

Hard words and math are explained in parentheses the first time they appear.

---

## Section 1 — Non-technical (the idea in plain English)

### What problem are we trying to solve?

Large language models (**LLMs** — AI systems that read text and write answers) often see the **same long documents** again and again: company policies, product docs, code, contracts, or passages pulled in by **RAG** (*retrieval-augmented generation* — “search my files, then answer using what you found”).

Every time the model reads a long prompt, it spends time and money on a first step called **prefill** (digesting the whole input before it can start replying). That waiting time is often called **TTFT** (*time to first token* — how long until the first word of the answer appears).

Today, servers already reuse work when the **start** of two prompts matches. That is **prefix caching** (save the beginning; skip redoing it). But documents often show up in the **middle** of the prompt, in a **different order**, or mixed with other docs. Prefix caching misses those. The server recomputes the same text from scratch.

### What is ContextWeave?

**ContextWeave** is a research project (and later, maybe a product) that asks:

> Can we safely reuse saved “memory” of recurring document chunks that are *not* at the start of the prompt — and only when that reuse is valid and does not quietly hurt answer quality?

It is **not** inventing a brand-new AI model. It is about **smarter reuse** of work that existing tools already almost do, plus a careful **planner** that chooses: reuse safely, repair a bit, or just do a full recompute.

### Why “safely” matters

If you glue saved pieces together carelessly, the model can give worse answers, or reuse data in the wrong security boundary (for example, mixing one user’s context into another’s). ContextWeave’s stance: **if we cannot prove reuse is valid, we refuse and fall back to full prefill.**

### How we decide if the project is worth it

We use **gates** (pass/fail checkpoints):

| Gate | Plain meaning |
|---|---|
| **G0** | “Is there enough repeating middle-of-prompt content to bother?” |
| **G1** | “Can we reproduce today’s best tools and measure them fairly?” |
| **G2+** | Later: “Does a smart per-request choice beat always using one fixed method?” |

Right now this is a **solo research project**. There is no design partner. Workloads are **synthetic** (fake but realistic request streams) or **corpus replay** (real local documents with a simulated request mix). So G0 results are marked **provisional** (*temporary / not final*) until a real production log exists — or until we explicitly accept provisional evidence for solo research.

### What we will not do first

- Train new models  
- Build a big production cloud product  
- Run heavy models on a personal laptop (policy: rent a cloud GPU when measurement starts)

### One-sentence summary (non-technical)

**ContextWeave checks whether recurring documents in LLM apps create enough wasted re-reading to justify a careful “reuse or recompute” planner — and it refuses unsafe reuse.**

---

## Section 2 — Technical (how it works, still in clear language)

### Background: prefill, KV cache, and prefix reuse

A transformer request has two stages:

1. **Prefill** — process the prompt; build **KV** tensors (*key/value caches* — internal “memory” the model keeps for each token so later steps do not redo all attention from scratch).  
2. **Decode** — generate output tokens using that KV memory.

**Prefix caching** stores KV for a matching prompt **prefix** (the shared beginning). ContextWeave treats that as the required baseline: work that prefix caching already covers is **not** the opportunity.

The opportunity is **recurring non-prefix chunks**: the same token sequences appear again, but not as a shared start — different position or order.

### Demand hypothesis (H1) and Gate G0

> **H1:** After normal prefix caching, a large share of remaining prefill tokens are exact repeats of earlier chunks, and those chunks are long enough to be worth loading from cache.

**Gate G0 (default bar):**

- At least **30%** of **post-prefix** prefill tokens are recurring non-prefix content  
  (*post-prefix* = tokens left after subtracting what native prefix cache already served)  
- **Median** chunk length ≥ **512** tokens  
  (*median* = the middle value when lengths are sorted; half the chunks are shorter, half longer)

**Working-set rule (v2.1):** it is not enough that tokens “ever” repeated in an infinite-memory log. We also simulate a limited cache (default **128 GB** of host storage for chunk KV) with **LRU** (*least recently used* — when full, throw out the oldest unused entry). The **decision** metric is: what fraction of post-prefix tokens would be **hits** under that budget?

Example from this repo’s Path C / `my_corpus` (provisional): unconstrained recurrence and LRU hit share both about **76.3%** at 128 GB — same denominator, so the old “79% > 74%” reporting bug is fixed.

### Why position and “assembly” matter (RoPE, without the rabbit hole)

Models use **RoPE** (*rotary position embeddings* — a way to encode “this token is at position 17” by rotating vectors). Moving a cached chunk to a new place often needs a **position rotation** of stored keys. That is considered a mostly solved sub-problem.

The harder quality issues when caching chunks independently are:

1. **Missing cross-chunk attention** — a chunk built alone never “saw” neighboring docs.  
2. **Attention sinks** — early tokens attract odd attention; each independent chunk can have its own sink.  
3. **Build-context dependence** — the chunk’s KV encodes the prefix/mask it was built under (**HijackKV**-style risk if you harvest mid-prompt).

**Mode A (normative):** ContextWeave does **not** cut KV slices out of live user prompts. Non-prefix artifacts are built only in **isolated canonical prefills** (a controlled build under a known fingerprint).

### What “planner” means here

Existing methods (examples from prior art, not ContextWeave inventions):

- Native **prefix** reuse  
- **CacheBlend**-style selective recompute / blend  
- **EPIC**-style sink / linking ideas  
- Full prefill (**C0** — the safe baseline)

**H2 (later phase):** no single fixed config wins everywhere; a per-request or per-slice **selector** might improve the quality/latency frontier — but only if measured after overhead.

ContextWeave’s intended product shape (deferred until research gates pass): a **validity-checked, quality-gated planner** that picks among those options and **falls back** when fingerprints, trust, or risk checks fail.

### Fingerprints, trust, and refusal

An artifact must carry a **fingerprint** (metadata identity): model revision, tokenizer, RoPE type, KV layout, build-context hash, content token identity, etc. Unknown or mismatched fields → **refuse reuse**.

**Trust namespaces** separate operator / tenant / untrusted content. Untrusted material is never admitted as shared reusable KV.

### Cost intuition (break-even, lightly)

Loading cached KV over a link only wins if load (+ any **repair**) is cheaper than full prefill.

Rough planning form (symbols explained):

\[
B^{*} \approx \frac{S_{\mathrm{KV}}}{T_{\mathrm{prefill}} - T_{\mathrm{repair}} - T_{\mathrm{other}}}
\]

- \(S_{\mathrm{KV}}\) — size of the KV bytes to move  
- \(T_{\mathrm{prefill}}\) — time of full prefill  
- \(T_{\mathrm{repair}}\) — time to fix / recompute a fraction of tokens  
- \(B^{*}\) — **break-even bandwidth** (how fast the link must be, or reuse loses)

Repair is **not** simply “15% of prefill time.” Dense linear layers and ragged attention are modeled with a **roofline** (compute vs memory-bandwidth limits). Short chunks or slow links can lose even when recurrence looks high.

### How prompts are assembled (token IDs, not string glue)

Rules (FR-02 / v2.1.1):

- Tokenize **chunk by chunk**  
- Append a **boundary** delimiter (default like `\n\n` as tokenizer-specific token IDs)  
- **Then** pad to the KV **block size** (e.g. 16) so pages align  
- Assemble by **concatenating token IDs** — never `tokenize(text_a + text_b)` (that can change tokenization at the join)

### What exists in this repository today (Phase 0)

| Piece | Role |
|---|---|
| Synthetic + Path C workloads | CPU-only demand traces |
| Prefix + working-set simulators | G0 metrics without a GPU |
| Cost model | Planning estimates (§7.5) |
| Fingerprint / provenance schemas | Validity + Mode A policy (metadata only) |
| Safety gate | No local model load unless `CONTEXTWEAVE_ALLOW_MODEL_LOAD=1` on a GPU host |

**Not started yet:** planner product, repair runtime, API service, distributed cache, RoPE kernels on GPU.

### Solo-project path (honest)

1. Treat provisional G0 (synthetic / corpus replay) as the demand signal for research.  
2. Next milestone when budget allows: **GPU smoke + baseline reproduction (G1)** on a rented host.  
3. Measure **answer preservation vs full prefill** on multi-hop tasks (causal-closure contract from recent PIC papers).  
4. Only then: Phase 1 rotation / oracle-selection studies (G2).  
5. If existing repairs still leave a gap → candidate mechanism **ResolventKV** (spectral causal closure); see [`Research/ResolventKV-adoption.md`](Research/ResolventKV-adoption.md).  
6. A real partner trace would upgrade G0 from provisional to final — nice, not required to *start* G1 as a solo researcher if results stay clearly labeled.

### One-sentence summary (technical)

**ContextWeave is a gated research program to measure whether validity-checked, non-prefix KV reuse — selected per request among existing training-free methods — can beat the best fixed baseline on recurring long-context workloads without silent quality or trust failures.**

---

## Where to go next

| If you want… | Open… |
|---|---|
| Full research charter | [`Docs/prd/contextweave_prd_v2.md`](prd/contextweave_prd_v2.md) |
| Binding fixes (working-set, Mode A, roofline) | [`Docs/prd/contextweave_prd_v2.1_amendments.md`](prd/contextweave_prd_v2.1_amendments.md) |
| ResolventKV research → what we adopt | [`Docs/Research/ResolventKV-adoption.md`](Research/ResolventKV-adoption.md) |
| Laptop / GPU safety | [`Docs/local-safety.md`](local-safety.md), [`Docs/cloud-gpu-rental.md`](cloud-gpu-rental.md) |
| Latest provisional G0 numbers | [`Docs/g0-provisional-synthetic.md`](g0-provisional-synthetic.md), [`Docs/g0-provisional-corpus-replay.md`](g0-provisional-corpus-replay.md) |
| Run CPU tools | [`README.md`](../README.md) |
