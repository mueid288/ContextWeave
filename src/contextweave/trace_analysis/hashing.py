"""Stable hashes for token-id sequences (CPU, no model)."""

from __future__ import annotations

import hashlib


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def hash_token_ids(token_ids: list[int]) -> str:
    return "sha256:" + sha256_hex(",".join(str(t) for t in token_ids))
