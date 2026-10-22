"""Shared G1 answer extraction / scoring (CPU-safe, no torch)."""

from __future__ import annotations

import re


_THINK_CLOSED_RE = re.compile(
    r"<think(?:ing)?>[\s\S]*?</think(?:ing)?>",
    re.IGNORECASE,
)
_THINK_OPEN_RE = re.compile(r"<think(?:ing)?>", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^a-z0-9\-]+")


def strip_think(text: str) -> str:
    """Remove Qwen-style thinking blocks (incl. <thinking> / unclosed) before scoring."""
    t = _THINK_CLOSED_RE.sub("", text or "")
    if not _THINK_OPEN_RE.search(t):
        return t.strip()
    parts = _THINK_OPEN_RE.split(t, maxsplit=1)
    head = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    keep: list[str] = []
    for ln in rest.splitlines():
        s = ln.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith(("okay", "ok,", "let me", "i need", "first,", "wait,")):
            continue
        if s.startswith("<"):
            continue
        keep.append(s)
    return (head + "\n" + "\n".join(keep)).strip()


def normalize(text: str) -> str:
    t = strip_think(text).strip().lower()
    return _PUNCT_RE.sub(" ", t).strip()


def _gold_as_word(text: str, gold: str) -> bool:
    """True if gold appears as a whole token/span, not a substring of a larger token."""
    if not gold:
        return False
    return re.search(rf"(?<![\w]){re.escape(gold)}(?![\w])", text, re.IGNORECASE) is not None


def _gold_negated(text: str, gold: str) -> bool:
    g = re.escape(gold)
    return (
        re.search(rf"\b(not|never|no)\b.{{0,40}}(?<![\w]){g}(?![\w])", text, re.IGNORECASE)
        is not None
        or re.search(rf"(?<![\w]){g}(?![\w]).{{0,40}}\b(not|never)\b", text, re.IGNORECASE)
        is not None
    )


def extract_answer(text: str, gold: str | None = None) -> str:
    """Best-effort short answer: prefer gold span if present, else first real line."""
    cleaned = strip_think(text)
    if gold and _gold_as_word(cleaned, gold) and not _gold_negated(cleaned, gold):
        m = re.search(rf"(?<![\w]){re.escape(gold)}(?![\w])", cleaned, re.IGNORECASE)
        if m:
            return cleaned[m.start() : m.end()]
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
    if _gold_as_word(cleaned, gold):
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
    raw_contains = _gold_as_word(cleaned, gold)
    contains = (norm_gold in norm_out.split()) or raw_contains
    # Word-boundary contains: avoid "2019" matching inside "20190".
    if not contains and re.search(
        rf"(?<![\w]){re.escape(norm_gold)}(?![\w])", norm_out
    ):
        contains = True
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
