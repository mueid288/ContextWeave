"""Shared G1 answer extraction / scoring (CPU-safe, no torch)."""

from __future__ import annotations

import re


_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^a-z0-9\-]+")


def strip_think(text: str) -> str:
    """Remove Qwen-style thinking blocks before scoring."""
    return _THINK_RE.sub("", text or "").strip()


def normalize(text: str) -> str:
    t = strip_think(text).strip().lower()
    return _PUNCT_RE.sub(" ", t).strip()


def extract_answer(text: str, gold: str | None = None) -> str:
    """Best-effort short answer: prefer gold span if present, else first real line."""
    cleaned = strip_think(text)
    if gold and gold.lower() in cleaned.lower():
        # Return the gold casing as it appears in the output when possible.
        idx = cleaned.lower().find(gold.lower())
        return cleaned[idx : idx + len(gold)]
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip separator / prompt echo / meta-instruction lines.
        if line.replace(" ", "") in {"##", "#", "###"} or set(line) <= {"#", " "}:
            continue
        low = line.lower()
        if low.startswith("the answer should") or low.startswith("okay"):
            continue
        if low.startswith("the answer is in the documents"):
            continue
        return line
    return cleaned.strip()


def is_garbage(text: str, gold: str) -> bool:
    """True if empty, pure echo/separators, or no coherent answer and no gold."""
    cleaned = strip_think(text)
    if not cleaned.strip():
        return True
    compact = re.sub(r"\s+", "", cleaned)
    if not compact or set(compact) <= {"#"}:
        return True
    # Pure separator / prompt echo patterns seen in prior blend fail.
    if re.fullmatch(r"[#\s]+", cleaned):
        return True
    low = cleaned.lower()
    # Invented / echoed questions — garbage even if gold appears inside the echo.
    if "what is the id of document" in low or re.search(r"#\s*#", cleaned):
        extracted = extract_answer(cleaned)
        # Only accept if extracted answer is exactly the gold (not a longer echo line).
        if normalize(extracted) != normalize(gold):
            return True
    if gold.lower() in low:
        return False
    extracted = extract_answer(cleaned)
    if not extracted or set(extracted.replace(" ", "")) <= {"#"}:
        return True
    # Very short nonsense with no alphanumeric content.
    if not re.search(r"[a-z0-9]", extracted, re.IGNORECASE):
        return True
    return False


def score_output(output: str, gold: str) -> dict:
    cleaned = strip_think(output)
    extracted = extract_answer(cleaned, gold=gold)
    norm_out = normalize(cleaned)
    norm_gold = normalize(gold)
    norm_ext = normalize(extracted)
    raw_contains = gold.lower() in cleaned.lower()
    contains = (norm_gold in norm_out) or raw_contains
    exact = norm_ext == norm_gold or extracted.strip() == gold
    garbage = is_garbage(cleaned, gold)
    return {
        "raw": output,
        "cleaned": cleaned,
        "extracted": extracted,
        "gold": gold,
        "contains": contains,
        "exact": exact,
        "garbage": garbage,
        "normalized": norm_out[:240],
    }
