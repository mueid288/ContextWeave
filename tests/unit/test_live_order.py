"""CPU tests for live canonical-order product path."""

from __future__ import annotations

import json
from pathlib import Path

from contextweave.product.frequency import FrequencyPrior
from contextweave.product.live_order import (
    apply_chat_documents,
    reorder_documents,
)


def test_frequency_prior_cold_then_hot():
    prior = FrequencyPrior(cold_start_n=2)
    assert prior.is_cold()
    docs = [
        {"document_id": "rare", "content": "r"},
        {"document_id": "hot", "content": "h"},
    ]
    # cold → by_doc_id (hot after rare alphabetically? "hot" < "rare")
    ordered = reorder_documents(docs, "by_frequency_desc", prior=prior)
    assert [d.document_id for d in ordered] == ["hot", "rare"]
    prior.observe(["hot"])  # extra to leave cold? already observed in reorder
    # After enough observations, frequency wins
    prior2 = FrequencyPrior(cold_start_n=1)
    prior2.observe(["hot", "hot", "hot", "rare"])
    assert not prior2.is_cold()
    ordered2 = reorder_documents(docs, "by_frequency_desc", prior=prior2, observe=False)
    assert ordered2[0].document_id == "hot"


def test_apply_chat_documents_injects_and_strips():
    prior = FrequencyPrior(cold_start_n=0)
    prior.observe(["hot"] * 5)
    body = {
        "model": "m",
        "messages": [{"role": "user", "content": "What city?"}],
        "cw_documents": [
            {"document_id": "rare", "content": "Rare doc"},
            {"document_id": "hot", "content": "Hot doc"},
        ],
        "cw_chunk_order": "by_frequency_desc",
    }
    out = apply_chat_documents(body, prior=prior)
    assert "cw_documents" not in out
    assert out["cw_meta"]["cw_applied"] is True
    assert out["cw_meta"]["cw_document_ids"][0] == "hot"
    content = out["messages"][0]["content"]
    assert "Hot doc" in content
    assert content.index("Hot doc") < content.index("Rare doc")
    assert "What city?" in content


def test_cli_reorder_json(tmp_path: Path):
    from contextweave.cli.serve_order import main

    req = tmp_path / "req.json"
    req.write_text(
        json.dumps(
            {
                "messages": [{"role": "user", "content": "q"}],
                "cw_documents": [
                    {"document_id": "b", "content": "B"},
                    {"document_id": "a", "content": "A"},
                ],
                "cw_chunk_order": "by_doc_id",
            }
        )
    )
    assert main(["--reorder-json", str(req), "--cold-start-n", "0"]) == 0
