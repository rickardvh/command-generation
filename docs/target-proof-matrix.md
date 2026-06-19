# Target Proof Matrix

Implemented generated targets must prove the generic surfaces they claim to own. Rendering files is not enough to mark a target implemented.

Required rows are projected from `TargetExtensionContract` by `required_target_proof_matrix_entries(...)`. Each row carries a stable `evidence_id` plus the proof `surface` so missing-evidence reports point at the target area that needs proof.

| Proof kind | Applies when | Owner |
| --- | --- | --- |
| `direct-operation-success` | The target declares an operation callable adapter. | Function/operation conformance |
| `direct-operation-structured-error` | The callable adapter declares structured error support. | Function/operation conformance |
| `cli-process-success` | The wrapper owns argv parsing or process behavior. | CLI/process conformance |
| `cli-process-parser-failure` | The wrapper owns argv parsing. | CLI/process conformance |
| `generated-artifact-freshness` | The target is implemented. | Freshness report or check mode |
| `generated-runtime-boundary` | The target is implemented. | Source/runtime boundary tests |
| `unsupported-primitive-target` | Target support depends on primitive declarations. | Primitive support validation |

Direct function conformance uses operation-shaped input values and checks operation results or structured errors. CLI/process conformance owns argv parsing, stdout/stderr, and exit-code behavior.

Hosts still own product-specific operation behavior. This package owns the reusable matrix shape, runners, freshness accounting, and primitive support checks.

`structured_target_proof_evidence_inventory()` records package-owned evidence for the targets currently implemented in this repository. Each evidence record declares:

- `surface`: `function`, `process`, `freshness`, `runtime-boundary`, or `primitive-support`.
- `evidence_type`: `conformance-case`, `ordinary-test`, `source-guard`, or `freshness-check`.
- `source`: the contract case, test id, or helper that proves the row.

`current_target_proof_evidence_inventory()` remains as the flat compatibility view of `evidence_id` and `source`. Matrix tests compare required rows against the structured inventory so new targets must declare evidence by surface and evidence type rather than adding anonymous test-name strings.
