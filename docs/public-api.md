# Public API Classification

`command_generation.__all__` is classified before 1.0 so hosts know which imports are intended compatibility surfaces.

- `stable`: supported host-facing API. Changes should be release-note-visible and semver-classified.
- `provisional`: usable during 0.x development, but callers should expect possible shape changes with clear release notes.
- Internal renderer helpers, generated code templates, and private primitive helpers are not exported from `__all__`.

| Symbol | Status |
| --- | --- |
| `BUILTIN_PORTABLE_PRIMITIVES` | provisional |
| `CanonicalCommandArtifact` | stable |
| `CliConformanceFailure` | stable |
| `CliConformanceResult` | stable |
| `CliConformanceTarget` | stable |
| `CommandGenerationHostManifest` | stable |
| `FunctionConformanceFailure` | stable |
| `FunctionConformanceResult` | stable |
| `FunctionConformanceTarget` | stable |
| `GeneratedOutput` | stable |
| `OperationConformanceCase` | stable |
| `PrimitiveContext` | provisional |
| `PrimitiveDefinition` | stable |
| `PrimitiveExecutionError` | provisional |
| `PrimitiveRegistry` | stable |
| `ProcessConformanceCase` | stable |
| `PUBLIC_API_CLASSIFICATION` | stable |
| `TargetExtensionContract` | stable |
| `TargetExtensionContractError` | stable |
| `TypescriptFunctionConformanceTarget` | provisional |
| `canonical_command_artifacts` | stable |
| `command_package_schema_path` | stable |
| `contract_conformance_cases_manifest` | stable |
| `conformance_ownership_inventory` | stable |
| `execute_primitive` | provisional |
| `expected_contract_fields` | provisional |
| `generate_command_packages` | stable |
| `generated_output_freshness_report` | stable |
| `invoke_typescript_operation` | provisional |
| `load_command_package_ir` | stable |
| `load_contract_conformance_case` | stable |
| `materialize_case_fixture` | stable |
| `missing_target_proof_matrix_entries` | stable |
| `operation_case_from_contract` | stable |
| `process_case_from_contract` | stable |
| `render_outputs` | stable |
| `required_target_proof_matrix_entries` | stable |
| `run_cli_conformance_case` | stable |
| `run_function_conformance_case` | stable |
| `run_operation_steps` | provisional |
| `run_typescript_function_conformance_case` | provisional |
| `selected_contract_fields` | provisional |
| `selected_result_fields` | provisional |
| `target_extension_schema_path` | stable |
| `target_support_matrix_entries` | stable |
| `typescript_function_target` | provisional |
| `validate_target_extension_contract` | stable |
