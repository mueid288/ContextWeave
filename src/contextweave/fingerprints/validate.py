"""FR-04 compatibility validation — reject unknown / mismatched fingerprints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contextweave.fingerprints.schema import (
    ArtifactFingerprint,
    UnknownFieldError,
    ValidationStatus,
)

# Static θ_i only (v2.1 §I / Gemini_3 §1.2). Dynamic NTK / YaRN / linear excluded.
SUPPORTED_ROPE_TYPES = frozenset({"default", "llama3"})


@dataclass
class ValidationResult:
    ok: bool
    status: ValidationStatus
    reason_codes: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status.value,
            "reason_codes": self.reason_codes,
            "details": self.details,
        }


def validate_artifact_fingerprint(
    fp: ArtifactFingerprint,
    *,
    allow_unpinned: bool = False,
) -> ValidationResult:
    """Validate completeness + build-context policy (no tensors)."""
    reasons: list[str] = []
    details: list[str] = []
    try:
        fp.validate_known(allow_unpinned=allow_unpinned)
    except UnknownFieldError as exc:
        return ValidationResult(
            ok=False,
            status=ValidationStatus.REJECTED,
            reason_codes=["unknown_fingerprint_field"],
            details=[str(exc)],
        )

    if not fp.build_context.canonical:
        reasons.append("build_context_not_canonical")
        details.append(
            "Build context is non-canonical; Mode A forbids non-canonical reuse (v2.1 §F)."
        )

    if fp.rope.rope_type not in SUPPORTED_ROPE_TYPES:
        reasons.append("unsupported_rope_type")
        details.append(
            f"rope_type={fp.rope.rope_type}; Phase 0/1 allow only {sorted(SUPPORTED_ROPE_TYPES)}"
        )

    if fp.kv.quantization not in {"none", "fp8", "int8"}:
        reasons.append("unsupported_kv_quantization")
        details.append(f"quantization={fp.kv.quantization}")

    if reasons:
        return ValidationResult(
            ok=False,
            status=ValidationStatus.REJECTED,
            reason_codes=reasons,
            details=details,
        )
    return ValidationResult(ok=True, status=ValidationStatus.VALIDATED)


def fingerprints_compatible(
    artifact: ArtifactFingerprint,
    request: ArtifactFingerprint,
) -> ValidationResult:
    """
    Compare stored artifact fingerprint to the request's model/runtime fingerprint.
    Content identity may differ (that's the point of reuse); model/rope/tokenizer/build
    policy must match.
    """
    base = validate_artifact_fingerprint(artifact)
    if not base.ok:
        return base
    req = validate_artifact_fingerprint(request)
    if not req.ok:
        return req

    reasons: list[str] = []
    details: list[str] = []

    if artifact.model.digest() != request.model.digest():
        reasons.append("model_mismatch")
    if artifact.tokenizer.digest() != request.tokenizer.digest():
        reasons.append("tokenizer_mismatch")
    if artifact.rope.digest() != request.rope.digest():
        reasons.append("rope_mismatch")
    if artifact.kv.to_dict() != request.kv.to_dict():
        reasons.append("kv_layout_mismatch")
    if artifact.runtime_schema_version != request.runtime_schema_version:
        reasons.append("runtime_schema_mismatch")
    if artifact.cache_schema_version != request.cache_schema_version:
        reasons.append("cache_schema_mismatch")
    if artifact.attention_impl != request.attention_impl:
        reasons.append("attention_impl_mismatch")
    if artifact.mask_assumptions != request.mask_assumptions:
        reasons.append("mask_mismatch")

    if not artifact.build_context.policy_allows_reuse():
        reasons.append("build_context_reuse_forbidden")
        details.append("Artifact build context fails policy.")
    elif (
        artifact.build_context.canonical
        and request.build_context.canonical
        and artifact.build_context.build_context_hash
        != request.build_context.build_context_hash
    ):
        reasons.append("build_context_hash_mismatch")
        details.append(
            "Canonical build-context hashes differ; refuse cross-context reuse."
        )

    if reasons:
        return ValidationResult(
            ok=False,
            status=ValidationStatus.REJECTED,
            reason_codes=reasons,
            details=details,
        )
    return ValidationResult(ok=True, status=ValidationStatus.VALIDATED)
