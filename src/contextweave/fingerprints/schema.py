"""FR-01 / FR-02 fingerprint schema (research harness, CPU-only).

If any required field is unknown, reuse must be rejected (PRD FR-01 / FR-04).
No model weights are loaded here — only metadata.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
import hashlib
import json


class UnknownFieldError(ValueError):
    """Raised when a validity-critical field is missing or explicitly unknown."""


class PositionStorageMode(str, Enum):
    POST_ROPE = "post_rope_keys"
    PRE_ROPE = "pre_rope_keys"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


_BLOCKED_REVISIONS = {
    "",
    "unknown",
    "UNKNOWN",
    "?",
    "desk-unpinned",
    "unpinned",
    "latest",
    "main",
}


def _require(value: Any, name: str, *, allow_unpinned: bool = False) -> Any:
    if value is None:
        raise UnknownFieldError(f"Required fingerprint field unknown: {name}")
    if isinstance(value, str):
        stripped = value.strip()
        blocked = {"", "unknown", "UNKNOWN", "?"}
        if not allow_unpinned:
            blocked |= _BLOCKED_REVISIONS
        if stripped in blocked:
            raise UnknownFieldError(f"Required fingerprint field unknown: {name}")
    return value


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ModelFingerprint:
    hf_repo: str
    revision: str  # immutable git / commit / tag
    weight_checksum: str | None  # optional until weights exist
    architecture: str
    num_layers: int
    num_attention_heads: int
    num_key_value_heads: int
    hidden_size: int
    head_dim: int | None = None

    def validate_known(self, *, allow_unpinned: bool = False) -> None:
        _require(self.hf_repo, "model.hf_repo")
        _require(self.revision, "model.revision", allow_unpinned=allow_unpinned)
        _require(self.architecture, "model.architecture")
        _require(self.num_layers, "model.num_layers")
        _require(self.num_attention_heads, "model.num_attention_heads")
        _require(self.num_key_value_heads, "model.num_key_value_heads")
        _require(self.hidden_size, "model.hidden_size")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self, *, allow_unpinned: bool = False) -> str:
        self.validate_known(allow_unpinned=allow_unpinned)
        return sha256_hex(canonical_json(self.to_dict()))


@dataclass(frozen=True)
class TokenizerFingerprint:
    name: str
    revision: str
    vocab_size: int | None = None

    def validate_known(self, *, allow_unpinned: bool = False) -> None:
        _require(self.name, "tokenizer.name")
        _require(self.revision, "tokenizer.revision", allow_unpinned=allow_unpinned)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self, *, allow_unpinned: bool = False) -> str:
        self.validate_known(allow_unpinned=allow_unpinned)
        return sha256_hex(canonical_json(self.to_dict()))


@dataclass(frozen=True)
class RopeFingerprint:
    rope_type: str  # e.g. "default", "llama3"
    rope_theta: float
    rope_scaling: dict[str, Any] | None
    position_convention: str  # e.g. "0-index", "hf-transformers"
    rotation_sign: str  # "+" or "-"
    feature_pairing: str  # "interleaved" | "split_half"
    position_storage_mode: PositionStorageMode
    max_position_embeddings: int | None = None

    def validate_known(self) -> None:
        _require(self.rope_type, "rope.rope_type")
        _require(self.rope_theta, "rope.rope_theta")
        _require(self.position_convention, "rope.position_convention")
        _require(self.rotation_sign, "rope.rotation_sign")
        _require(self.feature_pairing, "rope.feature_pairing")
        _require(self.position_storage_mode, "rope.position_storage_mode")
        # rope_scaling may be null (unscaled) — that is known, not unknown.

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["position_storage_mode"] = self.position_storage_mode.value
        return d

    def digest(self) -> str:
        self.validate_known()
        return sha256_hex(canonical_json(self.to_dict()))


@dataclass(frozen=True)
class BuildContextFingerprint:
    """Exact tokens/mask the chunk was built under (HijackKV-relevant).

    Mode A (v2.1 §F): only canonical isolated builds may be reused. There is no
    `allowed_noncanonical` bypass.
    """

    build_context_hash: str  # hash of prefix+chunk tokens and mask
    canonical: bool
    sink_prefix_token_count: int
    adapter_token_count: int = 0
    notes: str = ""

    def validate_known(self) -> None:
        _require(self.build_context_hash, "build_context.build_context_hash")
        if self.sink_prefix_token_count < 0:
            raise UnknownFieldError("build_context.sink_prefix_token_count invalid")

    def policy_allows_reuse(self) -> bool:
        self.validate_known()
        return self.canonical

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        self.validate_known()
        return sha256_hex(canonical_json(self.to_dict()))


@dataclass(frozen=True)
class ContentIdentity:
    """FR-02: document identity vs exact token sequence (v2.1 boundary rules)."""

    document_id: str
    content_hash: str
    token_ids_hash: str
    token_count: int
    chunking_config_id: str
    normalization_notes: str = "utf-8; strip; collapse_ws"
    boundary_token_ids: tuple[int, ...] = (198, 198)
    kv_block_size: int = 16
    padded_to_block: bool = True
    assembly_rule: str = "concat_token_ids_with_boundary"  # never retokenize joined text

    def validate_known(self) -> None:
        _require(self.document_id, "content.document_id")
        _require(self.content_hash, "content.content_hash")
        _require(self.token_ids_hash, "content.token_ids_hash")
        _require(self.chunking_config_id, "content.chunking_config_id")
        _require(self.assembly_rule, "content.assembly_rule")
        if self.kv_block_size <= 0:
            raise UnknownFieldError("content.kv_block_size invalid")
        if self.padded_to_block and self.token_count % self.kv_block_size != 0:
            raise UnknownFieldError(
                "content.token_count must be a multiple of kv_block_size when padded_to_block=true"
            )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["boundary_token_ids"] = list(self.boundary_token_ids)
        return d


@dataclass(frozen=True)
class KvLayoutFingerprint:
    dtype: str  # bf16 | fp16 | ...
    quantization: str  # "none" or format id
    layout: str  # e.g. "bhnd", "vllm_paged"
    head_dim: int
    num_kv_heads: int
    block_size: int = 16  # PagedAttention block size

    def validate_known(self) -> None:
        _require(self.dtype, "kv.dtype")
        _require(self.quantization, "kv.quantization")
        _require(self.layout, "kv.layout")
        _require(self.head_dim, "kv.head_dim")
        _require(self.num_kv_heads, "kv.num_kv_heads")
        if self.block_size <= 0:
            raise UnknownFieldError("kv.block_size invalid")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactFingerprint:
    """Full FR-01 fingerprint for one cache artifact."""

    model: ModelFingerprint
    tokenizer: TokenizerFingerprint
    rope: RopeFingerprint
    build_context: BuildContextFingerprint
    content: ContentIdentity
    kv: KvLayoutFingerprint
    attention_impl: str
    mask_assumptions: str
    runtime_schema_version: str
    cache_schema_version: str
    original_position_offsets: tuple[int, ...] | None = None

    def validate_known(self, *, allow_unpinned: bool = False) -> None:
        self.model.validate_known(allow_unpinned=allow_unpinned)
        self.tokenizer.validate_known(allow_unpinned=allow_unpinned)
        self.rope.validate_known()
        self.build_context.validate_known()
        self.content.validate_known()
        self.kv.validate_known()
        _require(self.attention_impl, "attention_impl")
        _require(self.mask_assumptions, "mask_assumptions")
        _require(self.runtime_schema_version, "runtime_schema_version")
        _require(self.cache_schema_version, "cache_schema_version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model.to_dict(),
            "tokenizer": self.tokenizer.to_dict(),
            "rope": self.rope.to_dict(),
            "build_context": self.build_context.to_dict(),
            "content": self.content.to_dict(),
            "kv": self.kv.to_dict(),
            "attention_impl": self.attention_impl,
            "mask_assumptions": self.mask_assumptions,
            "runtime_schema_version": self.runtime_schema_version,
            "cache_schema_version": self.cache_schema_version,
            "original_position_offsets": list(self.original_position_offsets)
            if self.original_position_offsets is not None
            else None,
        }

    def digest(self, *, allow_unpinned: bool = False) -> str:
        self.validate_known(allow_unpinned=allow_unpinned)
        return sha256_hex(canonical_json(self.to_dict()))


def hash_token_ids(token_ids: list[int]) -> str:
    return "sha256:" + sha256_hex(",".join(str(t) for t in token_ids))


def hash_build_context(
    *,
    prefix_token_ids: list[int],
    chunk_token_ids: list[int] | None = None,
    sink_prefix_token_count: int = 0,
    adapter_token_ids: list[int] | None = None,
    mask_id: str = "causal",
) -> str:
    """Hash of build *policy* (prefix/sink/adapter/mask), not chunk body.

    Chunk token identity belongs on ``ContentIdentity.token_ids_hash`` so
    ``fingerprints_compatible`` can allow cross-chunk reuse when policy matches.
    ``chunk_token_ids`` is accepted for call-site compatibility but ignored.
    """
    del chunk_token_ids  # content identity is separate; see docstring
    payload = {
        "prefix": prefix_token_ids,
        "sink_prefix_token_count": sink_prefix_token_count,
        "adapter": adapter_token_ids or [],
        "mask": mask_id,
    }
    return "sha256:" + sha256_hex(canonical_json(payload))
