# Target Proof Matrix

Implemented generated targets must prove the generic surfaces they claim to own. Rendering files is not enough to mark a target implemented.

Required rows are projected from `TargetExtensionContract` by `required_target_proof_matrix_entries(...)`:

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

`current_target_proof_evidence_inventory()` records the package-owned evidence ids for the targets currently implemented in this repository. Matrix tests compare required rows against that inventory rather than embedding ad hoc evidence ids in assertions.
