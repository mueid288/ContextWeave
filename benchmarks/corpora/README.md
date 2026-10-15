# Corpora (Path C)

Drop your own `.md` / `.txt` files into a folder, then:

```bash
python scripts/build_corpus_trace.py \
  --corpus-dir benchmarks/corpora/sample_docs \
  --analyze
```

- `sample_docs/` — bundled fictional Acme docs for a laptop dry-run  
- Your docs — replace `--corpus-dir` with any folder you have rights to use  

Output is a **provisional** partner_v1 trace (real text, simulated request mix). No model downloads.
