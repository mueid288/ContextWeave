"""CLI: own-corpus RAG demo (CPU client).

Examples::

  cw-rag-demo index
  cw-rag-demo retrieve "What is the SLA uptime target?"
  cw-rag-demo ask "What is the SLA uptime target?"
  cw-rag-demo bench --dry-build
  cw-rag-demo bench --base-url http://127.0.0.1:8080
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from contextweave.product.rag_demo.bench import (
    dry_build_report,
    load_questions,
    run_bench,
    write_report,
)
from contextweave.product.rag_demo.client import ask
from contextweave.product.rag_demo.index import ensure_index
from contextweave.product.rag_demo.retrieve import retrieve


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for cand in here.parents:
        if (cand / "pyproject.toml").exists():
            return cand
    return Path.cwd()


def resolve_corpus(explicit: Path | None) -> Path:
    """Prefer Own-corpus when it has docs; else sample_docs."""
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("CW_RAG_CORPUS")
    if env:
        return Path(env)
    own = Path("/Users/apple/Code/Own-corpus")
    if own.is_dir():
        docs = [
            p
            for p in own.rglob("*")
            if p.is_file()
            and p.suffix.lower() in {".md", ".txt"}
            and "Docs/Prd" not in str(p)
            and "/Docs/" not in str(p).replace("\\", "/")
        ]
        # Own-corpus currently empty of content docs — only use if real docs exist
        contentish = [
            p
            for p in docs
            if "prd" not in p.name.lower() and p.parent.name.lower() not in {"prd", "prds"}
        ]
        if contentish:
            return own
    root = _repo_root()
    return root / "benchmarks" / "corpora" / "sample_docs"


def _default_index_dir(root: Path) -> Path:
    return root / "artifacts" / "own-rag-demo" / "index"


def _default_questions(root: Path) -> Path:
    return root / "configs" / "product" / "own_rag_demo_questions.yaml"


def main(argv: list[str] | None = None) -> int:
    root = _repo_root()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--corpus",
        type=Path,
        default=None,
        help="Corpus directory (.md/.txt). Default: Own-corpus if populated, else sample_docs",
    )
    common.add_argument(
        "--index-dir",
        type=Path,
        default=None,
        help="Index directory (default artifacts/own-rag-demo/index)",
    )
    common.add_argument("--rebuild-index", action="store_true")
    common.add_argument("--chunk-chars", type=int, default=1000)
    common.add_argument("--overlap", type=int, default=100)
    common.add_argument("-k", type=int, default=3)
    common.add_argument(
        "--model",
        default=os.environ.get("CW_RAG_MODEL", "mistralai/Mistral-7B-Instruct-v0.2"),
    )
    common.add_argument(
        "--base-url",
        default=os.environ.get("CW_RAG_BASE_URL", "http://127.0.0.1:8080"),
        help="cw-serve-order base URL",
    )
    common.add_argument("--json", action="store_true")

    p = argparse.ArgumentParser(description=__doc__, parents=[common])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("index", help="Build/persist lexical index", parents=[common])

    pr = sub.add_parser("retrieve", help="Retrieve top-k (CPU)", parents=[common])
    pr.add_argument("question")

    pa = sub.add_parser("ask", help="Retrieve + POST through shim", parents=[common])
    pa.add_argument("question")
    pa.add_argument(
        "--chunk-order",
        default="by_frequency_desc",
        choices=["by_frequency_desc", "natural", "by_doc_id"],
    )
    pa.add_argument("--max-tokens", type=int, default=256)

    pb = sub.add_parser("bench", help="A/B warm latency (or --dry-build)", parents=[common])
    pb.add_argument(
        "--questions",
        type=Path,
        default=None,
        help="YAML question suite",
    )
    pb.add_argument("--warm-trials", type=int, default=8)
    pb.add_argument("--seed", type=int, default=7)
    pb.add_argument("--max-tokens", type=int, default=64)
    pb.add_argument("--timeout", type=float, default=180.0)
    pb.add_argument("--dry-build", action="store_true")
    pb.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write report JSON",
    )

    args = p.parse_args(argv)
    corpus = resolve_corpus(args.corpus)
    index_dir = args.index_dir or _default_index_dir(root)

    if args.cmd == "index":
        idx = ensure_index(
            corpus,
            index_dir,
            rebuild=True,
            chunk_chars=args.chunk_chars,
            overlap=args.overlap,
        )
        payload = {
            "corpus": str(corpus),
            "index_dir": str(index_dir),
            "n_chunks": len(idx),
            "meta": idx.meta,
        }
        print(json.dumps(payload, indent=2) if args.json else f"indexed {len(idx)} chunks → {index_dir}")
        return 0

    idx = ensure_index(
        corpus,
        index_dir,
        rebuild=args.rebuild_index,
        chunk_chars=args.chunk_chars,
        overlap=args.overlap,
    )

    if args.cmd == "retrieve":
        docs = retrieve(idx, args.question, k=args.k)
        if args.json:
            print(json.dumps({"retrieved": docs}, indent=2))
        else:
            print(f"corpus={corpus}")
            for d in docs:
                print(f"- {d['document_id']} ({len(d['content'])} chars)")
        return 0

    if args.cmd == "ask":
        docs = retrieve(idx, args.question, k=args.k)
        if not args.json:
            print("retrieved:", ", ".join(d["document_id"] for d in docs), flush=True)
        res = ask(
            base_url=args.base_url,
            question=args.question,
            documents=docs,
            model=args.model,
            chunk_order=args.chunk_order,
            max_tokens=args.max_tokens,
        )
        if args.json:
            print(
                json.dumps(
                    {
                        "answer": res.answer,
                        "wall_ms": res.wall_ms,
                        "cw_meta": res.cw_meta,
                        "retrieved_ids": res.retrieved_ids,
                    },
                    indent=2,
                )
            )
        else:
            print(res.answer)
            if res.cw_meta:
                print(f"\n# cw_meta: {json.dumps(res.cw_meta)}", flush=True)
            print(f"# wall_ms={res.wall_ms:.1f}", flush=True)
        return 0

    if args.cmd == "bench":
        qpath = args.questions or _default_questions(root)
        questions = load_questions(qpath)
        if args.dry_build:
            report = dry_build_report(
                index=idx, questions=questions, model=args.model, k=args.k, seed=args.seed
            )
            print(json.dumps(report, indent=2))
            return 0
        report = run_bench(
            index=idx,
            questions=questions,
            base_url=args.base_url,
            model=args.model,
            k=args.k,
            warm_trials=args.warm_trials,
            seed=args.seed,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
        )
        out = args.out
        if out is None:
            from datetime import date

            out = root / "artifacts" / f"own-rag-demo-{date.today().isoformat()}" / "report.json"
        write_report(report, out)
        summary = {
            "pass_heuristic": report["pass_heuristic"],
            "pass_functional": report["pass_functional"],
            "speedup": report["speedup_shuffled_over_frequency"],
            "shuf_p50": report["modes"]["shuffled"]["warm_p50_ms"],
            "freq_p50": report["modes"]["frequency"]["warm_p50_ms"],
            "out": str(out),
        }
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(
                f"pass_latency={summary['pass_heuristic']} "
                f"pass_functional={summary['pass_functional']} "
                f"speedup={summary['speedup']:.2f} "
                f"shuf_p50={summary['shuf_p50']:.0f}ms "
                f"freq_p50={summary['freq_p50']:.0f}ms "
                f"out={summary['out']}"
            )
        return 0 if report["pass_heuristic"] else 4

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
