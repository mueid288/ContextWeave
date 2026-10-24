"""Unit tests: bench dry-build constructs two mode payloads."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from contextweave.product.rag_demo.bench import build_mode_payload, dry_build_report, load_questions
from contextweave.product.rag_demo.index import build_index

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "benchmarks" / "corpora" / "sample_docs"
QUESTIONS = REPO / "configs" / "product" / "own_rag_demo_questions.yaml"


def test_load_questions_count():
    qs = load_questions(QUESTIONS)
    assert len(qs) >= 8
    assert qs[0]["gold"]


def test_build_mode_payload_differs():
    import random

    docs = [
        {"document_id": "z::chunk-000", "content": "z"},
        {"document_id": "a::chunk-000", "content": "a"},
        {"document_id": "m::chunk-000", "content": "m"},
    ]
    rng = random.Random(0)
    shuf = build_mode_payload(
        "shuffled", question="q", documents=docs, model="m", rng=rng
    )
    freq = build_mode_payload(
        "frequency", question="q", documents=docs, model="m", rng=rng
    )
    assert shuf["cw_chunk_order"] == "natural"
    assert freq["cw_chunk_order"] == "by_frequency_desc"
    assert len(shuf["cw_documents"]) == 3
    assert freq["cw_documents"] == docs


def test_dry_build_report():
    idx = build_index(SAMPLE, chunk_chars=1000, overlap=100)
    qs = load_questions(QUESTIONS)
    report = dry_build_report(index=idx, questions=qs, model="mistral", k=3, seed=7)
    assert "shuffled" in report["dry_build"]
    assert "frequency" in report["dry_build"]
    assert report["dry_build"]["frequency"]["cw_chunk_order"] == "by_frequency_desc"
    assert report["retrieved_ids"]


def test_cli_bench_dry_build():
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextweave.cli.rag_demo",
            "--corpus",
            str(SAMPLE),
            "bench",
            "--dry-build",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(REPO / "src")},
    )
    assert r.returncode == 0, r.stderr + r.stdout
    payload = json.loads(r.stdout)
    assert "frequency" in payload["dry_build"]
    assert "shuffled" in payload["dry_build"]
