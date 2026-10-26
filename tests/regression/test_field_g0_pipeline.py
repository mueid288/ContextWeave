"""field_g0 pipeline: ok mirrors gate; readiness gates; header download."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from contextweave.workloads import field_g0


def _partner_line(user_id: str, chunk_chars: int = 2200) -> dict:
    content = ("tokenword " * (chunk_chars // 10)).strip()
    # hash+count path used by partner_v1
    import hashlib

    h = "sha256:" + hashlib.sha256(content.encode()).hexdigest()
    return {
        "request_id": f"r-{user_id}-{chunk_chars}",
        "user_id": user_id,
        "query_type": "lookup",
        "prefix_token_count": 40,
        "chunks": [
            {
                "document_id": f"doc_{user_id}_md::chunk-000",
                "content_hash": h,
                "token_count": max(1, (len(content) + 3) // 4),
            }
        ],
        "query_token_count": 8,
        "timestamp": "2026-10-24T00:00:00+00:00",
        "meta": {"token_ids_synthetic": True, "source": "cw-field"},
    }


def test_unique_users(tmp_path: Path):
    raw = tmp_path / "partner_v1.jsonl"
    rows = [_partner_line("u1"), _partner_line("u2"), _partner_line("u1")]
    raw.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert field_g0._unique_users(raw) == 2


def test_below_min_traces(tmp_path: Path):
    art_root = tmp_path / "repo"
    tag = "t-min"
    art = art_root / "artifacts" / f"cw-field-g0-{tag}"
    art.mkdir(parents=True)
    raw = art / "partner_v1.jsonl"
    raw.write_text(json.dumps(_partner_line("u1")) + "\n", encoding="utf-8")
    code = field_g0.main(
        [
            "--skip-download",
            "--repo-root",
            str(art_root),
            "--tag",
            tag,
            "--min-traces",
            "5",
            "--token",
            "x",
        ]
    )
    assert code == 1
    summary = json.loads((art / "summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is False
    assert summary["reason"] == "below_min_traces"


def test_provisional_pass_not_bankable_without_allow(tmp_path: Path):
    """Synthetic partner_v1 can G0-PASS but must not set summary.ok without allow."""
    art_root = tmp_path / "repo"
    (art_root / "artifacts").mkdir(parents=True)
    tag = "unit-prov"
    art = art_root / "artifacts" / f"cw-field-g0-{tag}"
    art.mkdir(parents=True)
    raw = art / "partner_v1.jsonl"
    # Large chunks → median ≥ 512 → G0 PASS, still synthetic/provisional.
    lines = [
        json.dumps(_partner_line("u1", chunk_chars=2200)),
        json.dumps(_partner_line("u2", chunk_chars=2200)),
    ]
    raw.write_text("\n".join(lines) + "\n", encoding="utf-8")

    code = field_g0.main(
        [
            "--skip-download",
            "--repo-root",
            str(art_root),
            "--tag",
            tag,
            "--min-traces",
            "1",
            "--min-users",
            "1",
            "--token",
            "unused",
            # no --allow-provisional-ok
        ]
    )
    assert code == 3
    summary = json.loads((art / "summary.json").read_text(encoding="utf-8"))
    assert summary["g0"]["gate"] == "PASS"
    assert summary["ok"] is False
    assert summary["reason"] == "provisional_not_bankable"
    assert summary.get("provisional_g0") is True


def test_pipeline_ok_false_on_g0_fail(tmp_path: Path):
    art_root = tmp_path / "repo"
    (art_root / "artifacts").mkdir(parents=True)
    tag = "unit-fail"
    art = art_root / "artifacts" / f"cw-field-g0-{tag}"
    art.mkdir(parents=True)
    raw = art / "partner_v1.jsonl"
    # tiny chunks → median << 512 → G0 FAIL
    tiny = _partner_line("only", chunk_chars=80)
    raw.write_text(json.dumps(tiny) + "\n", encoding="utf-8")

    code = field_g0.main(
        [
            "--skip-download",
            "--repo-root",
            str(art_root),
            "--tag",
            tag,
            "--min-traces",
            "1",
            "--min-users",
            "1",
            "--token",
            "unused",
        ]
    )
    assert code == 2
    summary = json.loads((art / "summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is False
    assert summary["g0"]["gate"] == "FAIL"
    assert summary["n_users"] == 1


def test_fetch_traces_sends_auth_header(tmp_path: Path):
    dest = tmp_path / "out.jsonl"
    captured: dict = {}

    class _Resp:
        def read(self):
            return b'{"request_id":"1","user_id":"u","chunks":[]}\n'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=60):
        captured["url"] = req.full_url
        captured["auth"] = req.get_header("Authorization")
        captured["xadmin"] = req.get_header("X-admin-token") or req.get_header(
            "X-Admin-Token"
        )
        return _Resp()

    with patch("urllib.request.urlopen", fake_urlopen):
        n = field_g0._fetch_traces("http://example.test", "tok123", dest)
    assert n == 1
    assert "token=" not in captured["url"]
    assert captured["auth"] == "Bearer tok123"
    assert captured["xadmin"] == "tok123"
