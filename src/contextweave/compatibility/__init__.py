"""Compatibility validation (FR-04)."""

from contextweave.fingerprints.validate import (
    ValidationResult,
    fingerprints_compatible,
    validate_artifact_fingerprint,
)

__all__ = [
    "ValidationResult",
    "validate_artifact_fingerprint",
    "fingerprints_compatible",
]
