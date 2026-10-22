import pytest

from contextweave.fingerprints.schema import (
    ArtifactFingerprint,
    BuildContextFingerprint,
    ContentIdentity,
    KvLayoutFingerprint,
    ModelFingerprint,
    PositionStorageMode,
    RopeFingerprint,
    TokenizerFingerprint,
    UnknownFieldError,
    hash_build_context,
    hash_token_ids,
)
from contextweave.fingerprints.validate import (
    fingerprints_compatible,
    validate_artifact_fingerprint,
)
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


def _fp(
    *,
    canonical: bool = True,
    repo: str = "Qwen/Qwen3-8B",
    chunk: list[int] | None = None,
) -> ArtifactFingerprint:
    chunk = list(chunk) if chunk is not None else list(range(16))
    prefix = list(range(8))
    return ArtifactFingerprint(
        model=ModelFingerprint(
            hf_repo=repo,
            revision="abc123",
            weight_checksum=None,
            architecture="qwen3",
            num_layers=36,
            num_attention_heads=32,
            num_key_value_heads=8,
            hidden_size=4096,
            head_dim=128,
        ),
        tokenizer=TokenizerFingerprint(name="qwen", revision="tok1"),
        rope=RopeFingerprint(
            rope_type="default",
            rope_theta=1_000_000.0,
            rope_scaling=None,
            position_convention="hf-transformers",
            rotation_sign="+",
            feature_pairing="interleaved",
            position_storage_mode=PositionStorageMode.PRE_ROPE,
        ),
        build_context=BuildContextFingerprint(
            build_context_hash=hash_build_context(
                prefix_token_ids=prefix, chunk_token_ids=chunk
            ),
            canonical=canonical,
            sink_prefix_token_count=0,
        ),
        content=ContentIdentity(
            document_id="d1",
            content_hash="sha256:x",
            token_ids_hash=hash_token_ids(chunk),
            token_count=len(chunk),
            chunking_config_id="test",
            kv_block_size=16,
            padded_to_block=True,
        ),
        kv=KvLayoutFingerprint(
            dtype="bf16",
            quantization="none",
            layout="research_dense",
            head_dim=128,
            num_kv_heads=8,
            block_size=16,
        ),
        attention_impl="eager_gqa",
        mask_assumptions="causal_full",
        runtime_schema_version="r0",
        cache_schema_version="c0",
    )


def test_unknown_revision_rejected():
    fp = _fp()
    bad_model = ModelFingerprint(
        hf_repo="x",
        revision="unknown",
        weight_checksum=None,
        architecture="qwen3",
        num_layers=1,
        num_attention_heads=1,
        num_key_value_heads=1,
        hidden_size=1,
    )
    with pytest.raises(UnknownFieldError):
        bad_model.validate_known()
    # Swap via object reconstruction
    from dataclasses import replace

    bad = replace(fp, model=bad_model)
    result = validate_artifact_fingerprint(bad)
    assert not result.ok
    assert "unknown_fingerprint_field" in result.reason_codes


def test_noncanonical_build_context_rejected():
    result = validate_artifact_fingerprint(_fp(canonical=False))
    assert not result.ok
    assert "build_context_not_canonical" in result.reason_codes


def test_compatible_same_fingerprints():
    a = _fp()
    b = _fp()
    result = fingerprints_compatible(a, b)
    assert result.ok


def test_compatible_different_chunk_same_build_policy():
    """Cross-chunk reuse: content may differ; build-policy hash must still match."""
    from dataclasses import replace

    a = _fp(chunk=list(range(16)))
    other_chunk = list(range(100, 116))
    b = replace(
        a,
        content=replace(
            a.content,
            token_ids_hash=hash_token_ids(other_chunk),
            token_count=len(other_chunk),
        ),
        # Same prefix → same build_context_hash (chunk body excluded from hash).
        build_context=replace(
            a.build_context,
            build_context_hash=hash_build_context(
                prefix_token_ids=list(range(8)),
                chunk_token_ids=other_chunk,
            ),
        ),
    )
    assert a.build_context.build_context_hash == b.build_context.build_context_hash
    result = fingerprints_compatible(a, b)
    assert result.ok


def test_model_mismatch():
    a = _fp(repo="A")
    b = _fp(repo="B")
    result = fingerprints_compatible(a, b)
    assert not result.ok
    assert "model_mismatch" in result.reason_codes


def test_tokenizer_mismatch():
    from dataclasses import replace

    a = _fp()
    b = replace(a, tokenizer=replace(a.tokenizer, vocab_size=32000))
    result = fingerprints_compatible(a, b)
    assert not result.ok
    assert "tokenizer_mismatch" in getattr(result, "reasons", result.reason_codes)
    assert "tokenizer_mismatch" in result.reason_codes


def test_rope_mismatch():
    from dataclasses import replace

    a = _fp()
    b = replace(a, rope=replace(a.rope, rope_type="llama3"))
    result = fingerprints_compatible(a, b)
    assert not result.ok
    assert "rope_mismatch" in getattr(result, "reasons", result.reason_codes)
    assert "rope_mismatch" in result.reason_codes


def test_kv_layout_mismatch():
    from dataclasses import replace

    a = _fp()
    b = replace(a, kv=replace(a.kv, num_kv_heads=4))
    result = fingerprints_compatible(a, b)
    assert not result.ok
    assert "kv_layout_mismatch" in getattr(result, "reasons", result.reason_codes)
    assert "kv_layout_mismatch" in result.reason_codes


def test_cross_trust_reuse_denied():
    op = TrustNamespace("ops", TrustNamespaceKind.OPERATOR)
    tenant = TrustNamespace("tenant-1", TrustNamespaceKind.TENANT)
    with pytest.raises(CrossTrustReuseError):
        assert_reuse_allowed(tenant, op, artifact_from_untrusted_content=True)


def test_untrusted_same_namespace_denied():
    bad = TrustNamespace("pool", TrustNamespaceKind.UNTRUSTED)
    with pytest.raises(CrossTrustReuseError):
        assert_reuse_allowed(bad, bad, artifact_from_untrusted_content=False)


def test_lifecycle_must_be_available():
    op = TrustNamespace("ops", TrustNamespaceKind.OPERATOR)
    rec = ProvenanceRecord(
        artifact_id="a1",
        trust_namespace=op,
        fingerprint_digest="deadbeef",
        build_context_hash="sha256:x",
        built_in_canonical_context=True,
        lifecycle=ArtifactLifecycle.QUARANTINED,
    )
    with pytest.raises(CrossTrustReuseError):
        assert_reuse_allowed(op, op, artifact_from_untrusted_content=False, record=rec)


def test_dynamic_rope_rejected():
    from dataclasses import replace

    fp = _fp()
    bad_rope = replace(fp.rope, rope_type="yarn")
    bad = replace(fp, rope=bad_rope)
    result = validate_artifact_fingerprint(bad)
    assert not result.ok
    assert "unsupported_rope_type" in result.reason_codes


def test_unpinned_revision_rejected_by_default():
    from dataclasses import replace

    fp = _fp()
    bad_model = replace(fp.model, revision="desk-unpinned")
    bad = replace(fp, model=bad_model)
    result = validate_artifact_fingerprint(bad)
    assert not result.ok
    assert "unknown_fingerprint_field" in result.reason_codes
    ok = validate_artifact_fingerprint(bad, allow_unpinned=True)
    assert ok.ok


def test_quarantine():
    rec = ProvenanceRecord(
        artifact_id="a1",
        trust_namespace=TrustNamespace("ops", TrustNamespaceKind.OPERATOR),
        fingerprint_digest="deadbeef",
        build_context_hash="sha256:x",
        built_in_canonical_context=True,
        lifecycle=ArtifactLifecycle.AVAILABLE,
    )
    quarantine(rec, "audit_mismatch")
    assert rec.lifecycle == ArtifactLifecycle.QUARANTINED
    assert rec.quarantine_reason == "audit_mismatch"


def test_harvest_build_mode_rejected():
    from contextweave.provenance.trust import ArtifactBuildMode, IllegalBuildModeError
    from contextweave.provenance.trust import assert_reuse_allowed

    op = TrustNamespace("ops", TrustNamespaceKind.OPERATOR)
    with pytest.raises(IllegalBuildModeError):
        assert_reuse_allowed(
            op,
            op,
            artifact_from_untrusted_content=False,
            build_mode=ArtifactBuildMode.OPPORTUNISTIC_HARVEST,
        )


def test_mode_a_forbids_harvest():
    assert_canonical_build_mode(ArtifactBuildMode.CANONICAL_ISOLATED)
    with pytest.raises(IllegalBuildModeError):
        assert_canonical_build_mode(ArtifactBuildMode.OPPORTUNISTIC_HARVEST)
