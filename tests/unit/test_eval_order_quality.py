"""CPU smoke for product order-quality harness (no model call)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "product" / "eval_order_quality.py"


def test_dry_build_messages():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--base-url", "http://unused", "--dry-build"],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(REPO / "src")},
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    freq_city = next(x for x in payload["dry_build"]["frequency"] if x["id"] == "city")
    content = freq_city["messages"][0]["content"]
    # Warm prior makes doc-beta hottest → should appear before others
    assert content.index("doc-beta") < content.index("doc-gamma")
    rel = next(x for x in payload["dry_build"]["relevance"] if x["id"] == "city")
    assert "Karachi" in rel["messages"][0]["content"] or "doc-beta" in rel["messages"][0]["content"]
