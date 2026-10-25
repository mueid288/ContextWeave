# Dogfood C1 kit on cw-field

Prove the v0.2 kit policy on the live app: **frequency** (default) vs **natural**
(BM25 order, no C1 reorder). Measure with `cw-analyze-trace --compare-chunk-order`.

cw-field already implements the same frequency prior as the kit. `ORDER_MODE`
switches arms; traces log `meta.order_mode`.

## Homeserver — deploy

```bash
cd ~/Mueid/cw-field-traffic-app
git pull
# ensure ORDER_MODE=frequency in .env (or omit — default)
docker compose up -d --build web
curl -sS http://127.0.0.1:8787/health
# expect: "order_mode":"frequency","cw_c1_kit":"v0.2"
```

## Arm A — natural (control)

```bash
cd ~/Mueid/cw-field-traffic-app
# wipe only traces (keep corpora)
docker compose exec web sh -c 'rm -f /data/traces/partner_v1.jsonl /data/traces/partner_v1.count'

# set natural, rebuild web env
grep -q '^ORDER_MODE=' .env && sed -i 's/^ORDER_MODE=.*/ORDER_MODE=natural/' .env \
  || echo 'ORDER_MODE=natural' >> .env
docker compose up -d web
curl -sS http://127.0.0.1:8787/health   # order_mode=natural

# seed asks (use a real invite CODE)
INVITE=4024 ROUNDS=15 make seed
```

Pull + bank as natural:

```bash
cd ~/Mueid/ContextWeave && source .venv/bin/activate
export CW_FIELD_URL=http://127.0.0.1:8787 CW_FIELD_ADMIN_TOKEN='…'
python scripts/workloads/cw_field_pipeline.py --tag kit-natural --min-traces 10 --min-users 1
```

## Arm B — frequency (C1 kit)

```bash
cd ~/Mueid/cw-field-traffic-app
docker compose exec web sh -c 'rm -f /data/traces/partner_v1.jsonl /data/traces/partner_v1.count'
sed -i 's/^ORDER_MODE=.*/ORDER_MODE=frequency/' .env
docker compose up -d web
curl -sS http://127.0.0.1:8787/health   # order_mode=frequency
INVITE=4024 ROUNDS=15 make seed
```

```bash
cd ~/Mueid/ContextWeave && source .venv/bin/activate
python scripts/workloads/cw_field_pipeline.py --tag kit-frequency --min-traces 10 --min-users 1
```

## Measure with the kit

```bash
cd ~/Mueid/ContextWeave && source .venv/bin/activate
OUT=artifacts/product-kit-dogfood-$(date +%Y-%m-%d)
mkdir -p "$OUT"

# Prefer compare on the frequency arm (reorder replay); also compare each arm's raw trace
cw-analyze-trace --trace artifacts/cw-field-g0-kit-frequency/trace.jsonl \
  --compare-chunk-order \
  --report "$OUT/compare_frequency_arm.md" \
  --metrics-json "$OUT/compare_frequency_arm.json"

# Sanity: natural arm should already match "natural" mode in compare
cw-analyze-trace --trace artifacts/cw-field-g0-kit-natural/trace.jsonl \
  --compare-chunk-order \
  --report "$OUT/compare_natural_arm.md"
```

**Pass (desk):** on the frequency-arm trace, `by_frequency_desc` vs `natural` lifts
`share_prefix_cached` by ≥ **+2 pp** (same bar as field-order-ab).  
**Fail:** flat/negative → investigate cold start / too little shared-doc overlap.

## Notes

- Do not mix arms in one JSONL file.
- Keep `COLD_START_N=0` for a short seed if you want frequency active immediately:
  `echo COLD_START_N=0 >> .env` for the frequency arm only, then restore 32.
- This validates **policy + measurement**, not DeepSeek TTFT (that needs Layer 2 GPU).
