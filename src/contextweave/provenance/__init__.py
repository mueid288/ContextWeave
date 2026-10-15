"""Build-context provenance and trust boundaries (FR-13)."""

from contextweave.provenance.trust import (
    ArtifactBuildMode,
    ArtifactLifecycle,
    CrossTrustReuseError,
    IllegalBuildModeError,
    ProvenanceRecord,
    TrustNamespace,
    TrustNamespaceKind,
    assert_canonical_build_mode,
    assert_reuse_allowed,
    quarantine,
)

__all__ = [
    "ArtifactBuildMode",
    "ArtifactLifecycle",
    "CrossTrustReuseError",
    "IllegalBuildModeError",
    "ProvenanceRecord",
    "TrustNamespace",
    "TrustNamespaceKind",
    "assert_canonical_build_mode",
    "assert_reuse_allowed",
    "quarantine",
]
