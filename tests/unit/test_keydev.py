"""CPU tests for H3 runtime keydev threshold + planner wiring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from contextweave.planner.v0 import ConfigId, ReasonCode, RequestView, plan
from contextweave.provenance.trust import (
    ArtifactLifecycle,
    ProvenanceRecord,
    TrustNamespace,
    TrustNamespaceKind,
)
from contextweave.risk.keydev import (
    fit_threshold,
    mean_one_minus_cosine,
    predict_c3_quality_fail,
)


def _prov() -> tuple[ProvenanceRecord, TrustNamespace]:
    ns = TrustNamespace("ops", TrustNamespaceKind.OPERATOR)
    rec = ProvenanceRecord(
        artifact_id="a1",
        trust_namespace=ns,
        fingerprint_digest="deadbeef",
        build_context_hash="sha256:x",
        built_in_canonical_context=True,
        lifecycle=ArtifactLifecycle.AVAILABLE,
    )
    return rec, ns

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "scripts" / "phase1" / "eval_h3_keydev.py"
COLLECT = REPO / "scripts" / "phase1" / "collect_h3_keydev.py"


def test_mean_one_minus_cosine_identical_is_zero():
    v = [1.0, 0.0, 0.0]
    assert mean_one_minus_cosine([(v, v)]) == 0.0


def test_mean_one_minus_cosine_empty_is_unknown():
    assert mean_one_minus_cosine([]) is None


def test_predict_fail_closed_on_none():
    assert predict_c3_quality_fail(None, 0.1) is True
    assert predict_c3_quality_fail(0.05, 0.1) is False
    assert predict_c3_quality_fail(0.2, 0.1) is True


def test_planner_keydev_none_refuses_c3():
    rec, ns = _prov()
    d = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            keydev_score=None,
            keydev_threshold=0.5,
            provenance=rec,
            request_trust=ns,
        )
    )
    assert d.chosen != ConfigId.C3_EPIC
    assert (
        ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value
        in d.discarded[ConfigId.C3_EPIC.value]
    )


def test_fit_threshold_separates_scores():
    # fails have higher scores
    rows = [(0.1, False), (0.2, False), (0.8, True), (0.9, True)]
    fit = fit_threshold(rows, min_precision=0.9)
    assert fit.trainable
    assert fit.threshold <= 0.8
    assert predict_c3_quality_fail(0.9, fit.threshold)
    assert not predict_c3_quality_fail(0.1, fit.threshold)


def test_planner_keydev_allows_and_refuses():
    rec, ns = _prov()
    d_ok = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            keydev_score=0.05,
            keydev_threshold=0.5,
            provenance=rec,
            request_trust=ns,
        )
    )
    assert d_ok.chosen == ConfigId.C3_EPIC

    d_bad = plan(
        RequestView(
            has_validated_nonprefix_artifacts=True,
            keydev_score=0.9,
            keydev_threshold=0.5,
            provenance=rec,
            request_trust=ns,
        )
    )
    assert d_bad.chosen == ConfigId.C0_FULL_PREFILL
    assert (
        ReasonCode.QUALITY_RISK_EXCEEDS_POLICY.value
        in d_bad.discarded[ConfigId.C3_EPIC.value]
    )


def test_collect_cli_help_and_refuse():
    r = subprocess.run(
        [sys.executable, str(COLLECT), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "--filler-seed" in r.stdout


def test_eval_keydev_transfer(tmp_path: Path):
    def write(path: Path, rows: list[tuple[str, float, float]]) -> None:
        lines = []
        for i, (rid_suffix, keydev, q3) in enumerate(rows):
            rid = f"k{i:02d}_{rid_suffix}"
            lines.append(
                json.dumps(
                    {
                        "request_id": rid,
                        "config": "C0",
                        "quality": 1.0,
                        "ttft_ms": 1000.0,
                        "feasible": True,
                    }
                )
            )
            lines.append(
                json.dumps(
                    {
                        "request_id": rid,
                        "config": "C3",
                        "quality": q3,
                        "ttft_ms": 400.0,
                        "keydev": keydev,
                        "feasible": True,
                    }
                )
            )
        path.write_text("\n".join(lines) + "\n")

    train = tmp_path / "train.jsonl"
    test = tmp_path / "test.jsonl"
    write(train, [("ABC_city", 0.1, 1.0), ("BAC_year", 0.9, 0.0)])
    # Test scores stay on the same side of the fit threshold (0.9).
    write(test, [("ABC_city", 0.15, 1.0), ("BAC_year", 0.95, 0.0)])
    out = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            str(EVAL),
            "--train",
            str(train),
            "--test",
            str(test),
            "--out",
            str(out),
            "--json",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(out.read_text())
    assert payload["pass_heuristic"] is True
