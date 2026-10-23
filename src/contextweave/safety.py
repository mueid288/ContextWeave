"""Local machine safety: never load or download models unless explicitly allowed.

Default policy for laptop / CPU workstations: blocked.
Only a rented GPU box should set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1.
"""

from __future__ import annotations

import os

# Heavy inference stacks that must not be imported on the laptop.
_BLOCKED_IMPORTS = (
    "torch",
    "transformers",
    "vllm",
    "lmcache",
    "accelerate",
    "bitsandbytes",
)


class ModelLoadBlockedError(RuntimeError):
    """Raised when model load/download is attempted without explicit allow."""


def model_loads_allowed() -> bool:
    return os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD", "").strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
    }


def assert_model_load_allowed(action: str = "load or download a model") -> None:
    if model_loads_allowed():
        return
    raise ModelLoadBlockedError(
        f"Refusing to {action} on this machine. "
        "ContextWeave Phase 0 laptop policy: no local model inference. "
        "Use a rented GPU host and set CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 there only. "
        "See Docs/runbooks/local-safety.md."
    )


def get_heavy_imported_modules() -> list[str]:
    """Return names of blocked packages already imported (should be empty locally)."""
    import sys

    return [name for name in _BLOCKED_IMPORTS if name in sys.modules]


# Backward compatibility alias
assert_heavy_imports_absent = get_heavy_imported_modules
