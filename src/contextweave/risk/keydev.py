"""H3 runtime: Layer-0 isolated seam discontinuity gate (CPU threshold logic).

Score is mean (1 − cosine) at doc boundaries from EPIC isolated collect keys
(see ``g1_epic_bench._layer0_seam_keydev``). High score ⇒ refuse C3.
"""

from __future__ import annotations

from dataclasses import dataclass


def mean_one_minus_cosine(
    pairs: list[tuple[list[float], list[float]]],
) -> float:
    """Mean 1−cos over vector pairs; empty ⇒ 0.0 (treat as safe)."""
    if not pairs:
        return 0.0
    total = 0.0
    n = 0
    for a, b in pairs:
        if len(a) != len(b) or not a:
            continue
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na <= 0.0 or nb <= 0.0:
            continue
        total += 1.0 - (dot / (na * nb))
        n += 1
    return total / n if n else 0.0


def predict_c3_quality_fail(score: float | None, threshold: float) -> bool:
    """True ⇒ refuse C3. Unknown score ⇒ refuse (fail-closed)."""
    if score is None:
        return True
    return float(score) >= float(threshold)


@dataclass(frozen=True)
class KeydevThresholdFit:
    threshold: float
    train_precision: float
    trainable: bool
    notes: str = ""


def fit_threshold(
    scores_and_fails: list[tuple[float, bool]],
    *,
    min_precision: float = 0.9,
) -> KeydevThresholdFit:
    """Pick the smallest T with precision ≥ min_precision on train pairs.

    ``scores_and_fails``: (keydev_score, actual_c3_quality_fail).
    If no T meets the bar, return a fail-closed fit (T=0, refuse all).
    """
    if not scores_and_fails:
        return KeydevThresholdFit(
            threshold=0.0,
            train_precision=0.0,
            trainable=False,
            notes="empty train",
        )

    candidates = sorted({0.0, *[s for s, _ in scores_and_fails]})
    best: KeydevThresholdFit | None = None
    for t in candidates:
        tp = fp = 0
        for score, actual_fail in scores_and_fails:
            pred = score >= t
            if pred and actual_fail:
                tp += 1
            elif pred and not actual_fail:
                fp += 1
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        if prec >= min_precision and tp + fp > 0:
            fit = KeydevThresholdFit(
                threshold=t,
                train_precision=prec,
                trainable=True,
                notes=f"smallest T with prec>={min_precision}",
            )
            if best is None or t < best.threshold:
                best = fit
    if best is None:
        return KeydevThresholdFit(
            threshold=0.0,
            train_precision=0.0,
            trainable=False,
            notes="no T met precision bar; refuse-all",
        )
    return best
