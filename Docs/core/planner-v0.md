# Planner v0 (CPU)

PRD §7.6 rule-based planner. **No model load.**

```bash
python -c "
from contextweave.planner import plan, RequestView
from contextweave.provenance.trust import (
    ArtifactLifecycle, ProvenanceRecord, TrustNamespace, TrustNamespaceKind,
)
ns = TrustNamespace('ops', TrustNamespaceKind.OPERATOR)
rec = ProvenanceRecord(
    artifact_id='a1', trust_namespace=ns, fingerprint_digest='x',
    build_context_hash='sha256:x', built_in_canonical_context=True,
    lifecycle=ArtifactLifecycle.AVAILABLE,
)
print(plan(RequestView(
    has_validated_nonprefix_artifacts=True,
    keydev_score=0.05, keydev_threshold=0.5,
    provenance=rec, request_trust=ns,
)).to_dict())
"
```

## Rules (short)

1. Invalid artifacts → no non-prefix reuse.
2. Exact prefix → **C1**.
3. Non-prefix (**C3/C4**): FR-13 provenance + matching `request_build_context_hash`.
4. **C3:** also need keydev &lt; T **or** exact-distro slice-cal safe cell.
5. **C4:** refused on quality calibration (G1).
6. Else → **C0**.

Evidence: `Docs/pre-reg/pre-reg-fp-planner-gate.md`,
`Docs/pre-reg/pre-reg-fp-poison-suite.md`.
