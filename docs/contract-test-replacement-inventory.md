# Contract Test Replacement Inventory

This inventory is the command-generation closeout surface for replacing ordinary behavior regressions with contract-owned conformance cases. The goal is to preserve black-box behavior through smaller reusable cases, not to preserve the old pytest layout or duplicate lower-level primitive detail in higher-level tests.

## Converted

| Old ordinary coverage | Replacement owner | Case resource | Adapter/proof |
| --- | --- | --- | --- |
| Inline process success contract in `tests/test_public_api.py::test_contract_owned_conformance_case_runs_black_box_cli` | Package-owned process conformance case | `src/command_generation/conformance_cases/todo.list.process.json` | `process_case_from_contract` plus `run_cli_conformance_case` |
| Inline process output-drift contract in `tests/test_public_api.py::test_contract_owned_conformance_case_reports_output_drift` | Same package-owned process case, with a deliberately drifting test target | `src/command_generation/conformance_cases/todo.list.process.json` | Runner failure assertion only |
| Inline text stdout contract in `tests/test_public_api.py::test_contract_owned_conformance_case_checks_text_stdout` | Package-owned process conformance case | `src/command_generation/conformance_cases/todo.list-text.process.json` | `stdout.contains` contract |
| Inline text stdout drift contract in `tests/test_public_api.py::test_contract_owned_conformance_case_reports_text_stdout_drift` | Same package-owned text case, with a deliberately drifting test target | `src/command_generation/conformance_cases/todo.list-text.process.json` | Runner failure assertion only |
| Inline function success contract in `tests/test_public_api.py::test_contract_owned_operation_case_runs_function_adapter` | Package-owned operation conformance case | `src/command_generation/conformance_cases/todo.list.operation.json` | `operation_case_from_contract` plus `run_function_conformance_case` |
| Inline function error contract in `tests/test_public_api.py::test_contract_owned_operation_case_checks_expected_function_error` | Package-owned operation conformance case | `src/command_generation/conformance_cases/todo.list-error.operation.json` | Structured expected-error contract |

## Kept Ordinary

| Surface | Reason |
| --- | --- |
| `tests/test_public_api.py` schema loading, non-AW fixture rendering, canonical artifacts, freshness accounting, source-literal guards, primitive registry, and facade patch semantics | These are API, generator, schema, packaging, or adapter-mechanics tests rather than reusable operation behavior cases. |
| `tests/test_primitive_executor.py` primitive unit behavior and narrow error handling | Primitive internals remain ordinary unit tests; composite operation behavior should assume primitive unit tests and assert only higher-order composition behavior. |
| `tests/primitive_conformance.py` standalone primitive smoke | This is a maintainer smoke script for portable primitive availability, not the canonical behavior matrix. |
| `src/command_generation/conformance.py` runner internals | Runner parsing, normalization, failure messages, and fixture materialization stay ordinary because they test the test harness itself. |

## Merged Or Deleted

No additional ordinary tests were deleted in this slice. The bulk reduction was moving repeated contract payloads out of pytest bodies and into reusable package-owned resources. Higher-level tests now reference the same contract resources instead of copying the behavior shape.

## Boundary

Package-owned cases belong here when they describe generic process, function, adapter, primitive, or generator behavior reusable by consumers. Product-specific operation contracts, proof routing, lifecycle behavior, installed-package checks, wrapper transport policy, and host runtime primitives remain in the consumer repository.
