"""FR-13 provenance and trust boundaries (fields + policy; no distributed store).

PRD v2.1 amendment F (Mode A): non-prefix artifacts are built only in isolated
canonical prefills. Mid-prompt opportunistic harvest is forbidden.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
import time


class ArtifactBuildMode(str, Enum):
    """How a non-prefix KV artifact was created."""

    CANONICAL_ISOLATED = "canonical_isolated"  # Mode A — only allowed mode
    # Explicitly unsupported (kept for rejection messaging):
    OPPORTUNISTIC_HARVEST = "opportunistic_harvest"


class TrustNamespaceKind(str, Enum):
    OPERATOR = "operator"  # canonical, operator-controlled builds
    TENANT = "tenant"  # single-tenant content
    UNTRUSTED = "untrusted"  # user-supplied / untrusted sources


class ArtifactLifecycle(str, Enum):
    REQUESTED = "requested"
    TOKENIZED = "tokenized"
    COMPUTING = "computing"
    VALIDATED = "validated"
    AVAILABLE = "available"
    QUARANTINED = "quarantined"
    EXPIRED = "expired"
    DELETED = "deleted"


@dataclass(frozen=True)
class TrustNamespace:
    name: str
    kind: TrustNamespaceKind

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind.value}


@dataclass
class ProvenanceRecord:
    artifact_id: str
    trust_namespace: TrustNamespace
    fingerprint_digest: str
    build_context_hash: str
    built_in_canonical_context: bool
    build_mode: ArtifactBuildMode = ArtifactBuildMode.CANONICAL_ISOLATED
    source_content_hashes: list[str] = field(default_factory=list)
    lifecycle: ArtifactLifecycle = ArtifactLifecycle.REQUESTED
    created_at_unix: float = field(default_factory=time.time)
    quarantine_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "trust_namespace": self.trust_namespace.to_dict(),
            "fingerprint_digest": self.fingerprint_digest,
            "build_context_hash": self.build_context_hash,
            "built_in_canonical_context": self.built_in_canonical_context,
            "build_mode": self.build_mode.value,
            "source_content_hashes": list(self.source_content_hashes),
            "lifecycle": self.lifecycle.value,
            "created_at_unix": self.created_at_unix,
            "quarantine_reason": self.quarantine_reason,
        }


class CrossTrustReuseError(PermissionError):
    pass


class IllegalBuildModeError(ValueError):
    pass


def assert_canonical_build_mode(mode: ArtifactBuildMode) -> None:
    """Non-prefix artifacts must use Mode A (isolated canonical prefill)."""
    if mode != ArtifactBuildMode.CANONICAL_ISOLATED:
        raise IllegalBuildModeError(
            f"Build mode {mode.value} forbidden. "
            "ContextWeave never harvests non-prefix KV from mid-prompt live requests "
            "(PRD v2.1 amendment F). Use canonical_isolated prefills only."
        )


def assert_reuse_allowed(
    artifact_ns: TrustNamespace,
    request_ns: TrustNamespace,
    *,
    artifact_from_untrusted_content: bool,
    build_mode: ArtifactBuildMode = ArtifactBuildMode.CANONICAL_ISOLATED,
    record: ProvenanceRecord | None = None,
) -> None:
    """
    Artifacts built from untrusted content are never reused (same-namespace included).
    Lifecycle must be AVAILABLE; build must be canonical Mode A.
    """
    assert_canonical_build_mode(build_mode)

    if artifact_from_untrusted_content or artifact_ns.kind == TrustNamespaceKind.UNTRUSTED:
        raise CrossTrustReuseError(
            "Refuse reuse of KV artifact built from untrusted content or in an untrusted namespace."
        )

    if record is not None:
        if not record.built_in_canonical_context:
            raise CrossTrustReuseError(
                f"Artifact {record.artifact_id} was not built in a canonical context."
            )
        if record.lifecycle != ArtifactLifecycle.AVAILABLE:
            raise CrossTrustReuseError(
                f"Artifact {record.artifact_id} is not available for reuse "
                f"(lifecycle={record.lifecycle.value})."
            )
        assert_canonical_build_mode(record.build_mode)
        if record.trust_namespace != artifact_ns:
            raise CrossTrustReuseError(
                f"Refuse reuse: record trust namespace {record.trust_namespace} "
                f"does not match artifact_ns {artifact_ns}"
            )

    if artifact_ns.name != request_ns.name or artifact_ns.kind != request_ns.kind:
        raise CrossTrustReuseError(
            f"Refuse cross-namespace reuse: artifact={artifact_ns.to_dict()} "
            f"request={request_ns.to_dict()}"
        )


def quarantine(record: ProvenanceRecord, reason: str) -> ProvenanceRecord:
    record.lifecycle = ArtifactLifecycle.QUARANTINED
    record.quarantine_reason = reason
    return record
