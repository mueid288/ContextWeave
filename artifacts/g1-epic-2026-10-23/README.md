# G1 EPIC (LegoLink) artifacts — 2026-10-23

Session `cw-epic`. Fast path: `vllm==0.7.0` wheel + DerekHJH/epic Python overlay,
Python 3.11 uv venv, `Mistral-7B-Instruct-v0.2`.

| File | Role |
|---|---|
| `g1_epic.json` | Bench: quality OK / latency FAIL (`pass_heuristic: false`) |

- full_prefill ~**235 ms**; kvlink-8 ~**332 ms**; speedup **0.71×**
- Both outputs contain gold `Karachi`
- Narrative: `Docs/experiment-log.md` (2026-10-23 EPIC entry)
