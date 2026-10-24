"""CLI entry: pull cw-field traces and run Gate G0."""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    script = Path(__file__).resolve().parents[3] / "scripts/workloads/cw_field_pipeline.py"
    # When installed editable from repo root; fall back to CWD discovery
    if not script.is_file():
        script = Path.cwd() / "scripts/workloads/cw_field_pipeline.py"
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
