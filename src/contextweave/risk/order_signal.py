"""H3: order-permutation risk for EPIC/C3 (CPU-only).

Fit on ``artifacts/phase1-oracle-2026-10-23/``: C3 gold-contains failed iff
doc order was ``ACB`` (city) or ``BAC`` (year). Rule is fail-closed when order
is unknown.
"""

from __future__ import annotations

# Permutations where LegoLink-8 denied the gold fact on the oracle suite.
UNSAFE_EPIC_ORDERS: frozenset[str] = frozenset({"ACB", "BAC"})


def predict_c3_quality_fail(chunk_order: str | None) -> bool:
    """Return True ⇒ refuse C3 (predict quality fail or unknown).

    ``chunk_order`` is a 3-letter permutation of ABC for the synthetic suite
    (e.g. ``\"BCA\"``). ``None`` / empty ⇒ unsafe (fail closed).
    """
    if not chunk_order:
        return True
    key = "".join(c for c in chunk_order.upper() if c.isalpha())
    if len(key) != 3:
        return True
    return key in UNSAFE_EPIC_ORDERS
