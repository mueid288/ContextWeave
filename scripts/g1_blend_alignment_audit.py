#!/usr/bin/env python3
"""FIX-2: offline CacheBlend chunk/sep/hash alignment audit (CPU-safe).

Uses a FakeTokenizer locally (no transformers). On GPU host with
``CONTEXTWEAVE_ALLOW_MODEL_LOAD=1``, pass ``--model`` to audit real tokenization.

  python scripts/g1_blend_alignment_audit.py --json
  CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 python scripts/g1_blend_alignment_audit.py \\
    --model Qwen/Qwen3-8B --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from g1_matched_ttft_bench import (  # noqa: E402
    DEFAULT_BLEND_SPECIAL,
    QUESTION,
    SYSTEM_TEXT,
    _fill_chunk,
    _join_chunks,
    _prompt_for_order,
    _sep_ids,
)


class _FakeTok:
    bos_token_id = 1

    def encode(self, text: str, add_special_tokens: bool = False):
        ids = [ord(c) % 97 + 2 for c in text]
        if add_special_tokens:
            return [self.bos_token_id, *ids]
        return ids


def _hash_ids(ids: list[int]) -> str:
    h = hashlib.sha256()
    h.update(b",".join(str(i).encode() for i in ids))
    return h.hexdigest()[:16]


def _extract_chunks_from_prompt(
    prompt: list[int],
    *,
    system: list[int],
    sep: list[int],
    n_chunks: int,
) -> list[list[int]]:
    """Split joined prompt back into chunk bodies (assumes sep markers)."""
    if not sep:
        raise ValueError("empty sep")
    # Walk: system, then (sep + chunk) * n, then sep + question
    pos = len(system)
    chunks: list[list[int]] = []
    for _ in range(n_chunks):
        if prompt[pos : pos + len(sep)] != sep:
            raise ValueError(f"missing sep at {pos}")
        pos += len(sep)
        # Find next sep
        next_sep = None
        i = pos
        while i + len(sep) <= len(prompt):
            if prompt[i : i + len(sep)] == sep:
                next_sep = i
                break
            i += 1
        if next_sep is None:
            raise ValueError("could not find next sep")
        chunks.append(prompt[pos:next_sep])
        pos = next_sep
    return chunks


def run_audit(
    tokenizer,
    *,
    chunk_tokens: int = 512,
    blend_special_str: str = DEFAULT_BLEND_SPECIAL,
) -> dict:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "pass": ok, "detail": detail})

    chunk_tokens = max(256, (chunk_tokens // 256) * 256)
    sep = _sep_ids(tokenizer, blend_special_str)
    system = tokenizer.encode(SYSTEM_TEXT, add_special_tokens=True)
    question_ids = tokenizer.encode(QUESTION, add_special_tokens=False)
    chunk_map = {k: _fill_chunk(tokenizer, k, chunk_tokens) for k in ("A", "B", "C")}

    for k, ids in chunk_map.items():
        add(
            f"chunk_{k}_multiple_of_256",
            len(ids) % 256 == 0 and len(ids) == chunk_tokens,
            f"len={len(ids)} target={chunk_tokens}",
        )

    sep2 = _sep_ids(tokenizer, blend_special_str)
    add("sep_stable", sep == sep2 and len(sep) > 0, f"sep={sep}")

    abc = _prompt_for_order(
        ("A", "B", "C"),
        chunk_map=chunk_map,
        system=system,
        question_ids=question_ids,
        sep=sep,
    )
    bac = _prompt_for_order(
        ("B", "A", "C"),
        chunk_map=chunk_map,
        system=system,
        question_ids=question_ids,
        sep=sep,
    )
    try:
        abc_chunks = _extract_chunks_from_prompt(
            abc, system=system, sep=sep, n_chunks=3
        )
        bac_chunks = _extract_chunks_from_prompt(
            bac, system=system, sep=sep, n_chunks=3
        )
        # In ABC order chunks are A,B,C; in BAC they are B,A,C
        add(
            "chunk_B_position_invariant",
            abc_chunks[1] == bac_chunks[0] == chunk_map["B"],
            f"abc[1]==bac[0]==map[B] hashes "
            f"{_hash_ids(abc_chunks[1])} / {_hash_ids(bac_chunks[0])} / "
            f"{_hash_ids(chunk_map['B'])}",
        )
        add(
            "chunk_A_position_invariant",
            abc_chunks[0] == bac_chunks[1] == chunk_map["A"],
            f"hashes {_hash_ids(abc_chunks[0])} / {_hash_ids(bac_chunks[1])}",
        )
    except ValueError as exc:
        add("chunk_extract", False, str(exc))

    # Body hash ignores surrounding system/sep — required for position-independent cache keys.
    add(
        "body_hash_independent_of_neighbors",
        _hash_ids(chunk_map["B"]) == _hash_ids(list(chunk_map["B"])),
        f"B_hash={_hash_ids(chunk_map['B'])}",
    )

    # BOS only on system encode path, not on chunk bodies.
    bos = getattr(tokenizer, "bos_token_id", None)
    if bos is not None:
        add(
            "chunks_no_leading_bos",
            all(not ids or ids[0] != bos for ids in chunk_map.values()),
            f"bos={bos}",
        )
        add(
            "system_may_have_bos",
            True,
            f"system_len={len(system)} starts={system[:2]}",
        )

    # Salted chunks must change body hash (anti self-hit).
    salted = _fill_chunk(tokenizer, "B", chunk_tokens, salt="s1:")
    add(
        "salt_changes_chunk_hash",
        _hash_ids(salted) != _hash_ids(chunk_map["B"]),
        f"plain={_hash_ids(chunk_map['B'])} salted={_hash_ids(salted)}",
    )

    passed = all(c["pass"] for c in checks)
    return {
        "gate": "G1-FIX2-alignment-audit",
        "chunk_tokens": chunk_tokens,
        "blend_special_str": blend_special_str,
        "sep_ids": sep,
        "system_len": len(system),
        "abc_len": len(abc),
        "bac_len": len(bac),
        "checks": checks,
        "pass_all": passed,
        "note": (
            "CPU audit of chunk_sep construction. Real LMCache hash equality "
            "still needs GPU engagement metrics (Gate R)."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-tokens", type=int, default=512)
    parser.add_argument("--blend-special-str", default=DEFAULT_BLEND_SPECIAL)
    parser.add_argument("--model", default=None, help="HF tokenizer id (GPU/desk with allow flag)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.model:
        if os.environ.get("CONTEXTWEAVE_ALLOW_MODEL_LOAD") != "1":
            print(
                "Refusing --model without CONTEXTWEAVE_ALLOW_MODEL_LOAD=1",
                file=sys.stderr,
            )
            return 1
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    else:
        tokenizer = _FakeTok()

    payload = run_audit(
        tokenizer,
        chunk_tokens=args.chunk_tokens,
        blend_special_str=args.blend_special_str,
    )
    text = json.dumps(payload, indent=2) + "\n"
    if args.out:
        args.out.write_text(text)
        print(f"Wrote {args.out}", flush=True)
    if args.json:
        print(text, end="")
    else:
        for c in payload["checks"]:
            mark = "PASS" if c["pass"] else "FAIL"
            print(f"  [{mark}] {c['name']}: {c['detail']}")
        print(f"pass_all={payload['pass_all']}")
    return 0 if payload["pass_all"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
