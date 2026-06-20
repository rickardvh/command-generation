# Public API Classification

`command_generation.__all__` is the stable 1.0 package-level public API. Runtime executor plumbing, target renderer modules, generated code templates, and direct TypeScript invocation helpers remain module-internal surfaces rather than package-level exports.

| Symbol | Status |
| --- | --- |
| `BUILTIN_PORTABLE_PRIMITIVES` | stable |
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
| `PrimitiveDefinition` | stable |
| `PrimitiveRegistry` | stable |
| `ProcessConformanceCase` | stable |
| `PUBLIC_API_CLASSIFICATION` | stable |
| `TargetExtensionContract` | stable |
| `TargetExtensionContractError` | stable |
| `canonical_command_artifacts` | stable |
| `command_package_schema_path` | stable |
| `contract_conformance_cases_manifest` | stable |
| `conformance_ownership_inventory` | stable |
| `generate_command_packages` | stable |
| `generated_output_freshness_report` | stable |
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
| `target_extension_schema_path` | stable |
| `target_support_matrix_entries` | stable |
| `validate_target_extension_contract` | stable |

## Stable API Audit

| Symbol | Host-facing purpose | Stable contract | Compatibility rationale |
| --- | --- | --- | --- |
| `PUBLIC_API_CLASSIFICATION` | Lets hosts and tests inspect the compatibility tier for every exported symbol. | Mapping keys match `command_generation.__all__`; values are `stable`. | Consumers need a machine-readable way to reject accidental stable-surface drift before and after 1.0. |
| `command_package_schema_path` | Gives hosts the packaged command package IR schema path. | Returns a readable `Path` for the canonical packaged schema. | Schema lookup should not depend on repository layout or editable installs. |
| `load_command_package_ir` | Loads and validates host command package IR before rendering or proof. | Accepts a manifest path and schema path, returns the normalized manifest mapping, and canonicalizes supported schema aliases. | This is the primary host entry point for reading source IR under semver-controlled schema behavior. |
| `CommandGenerationHostManifest` | Carries host-owned generation inputs without embedding product policy in generic generation code. | Frozen dataclass accepted directly or via `from_mapping(...)`; relative paths resolve against `repo_root`; stable fields include `generated_root`, `package_ids`, `contract_roots`, `primitive_registry`, `target_bindings`, `python_primitive_support_path`, `typescript_primitive_support_path`, and `operation_schema_version`. | Hosts need one stable value object for primitive support files, contract roots, target bindings, and schema version selection. |
| `PrimitiveDefinition` | Describes one primitive that generated operations may reference. | Frozen dataclass with stable fields for identity, kind, schema refs, effects, target support, owner, conformance refs, and unsupported-target behavior. | Primitive declarations are host/package contract data and must remain inspectable without importing renderer internals. |
| `PrimitiveRegistry` | Provides registry lookup, support checks, merge behavior, and JSON serialization for primitive declarations. | Construct from definitions, query by id, require declarations, ensure target support, list ids, merge registries, and serialize via `to_jsonable()`. | Hosts need stable registry mechanics while individual host-owned primitive implementations stay outside this package. |
| `BUILTIN_PORTABLE_PRIMITIVES` | Exposes the package-owned built-in primitive registry. | Registry entries are portable package primitives plus explicit host-owned bridge IDs; product-shaped transitional compatibility IDs are not part of the 1.0 registry. | Hosts need a stable baseline registry they can merge with host-owned primitive declarations. |
| `CanonicalCommandArtifact`, `canonical_command_artifacts` | Exposes generated artifact identity metadata for canonical package outputs. | The dataclass and helper return canonical artifact records with stable path/content/provenance shape used by downstream proof. | Generated package freshness and release proof need package-owned artifact metadata without reaching into target renderers. |
| `GeneratedOutput` | Represents an in-memory rendered file before write or freshness checking. | Dataclass values carry a target `Path` and desired text content. | Hosts can compare or write generated output without depending on private renderer implementation details. |
| `render_outputs` | Renders command package outputs in memory. | Accepts a loaded manifest, `repo_root`, source path, regenerate command, and optional host manifest; returns `list[GeneratedOutput]` without writing files. | This is the stable dry-run/render boundary for stale checks, custom proof, and host integration. |
| `generate_command_packages` | Writes or checks rendered command package outputs. | Uses the same rendering inputs as `render_outputs`; with `check=True` returns stale relative paths, otherwise writes files and returns an empty stale list. | Host CI and maintainers need a stable write/check command boundary. |
| `generated_output_freshness_report` | Summarizes output freshness and per-target-family coverage without rewriting files. | Accepts rendered outputs, `repo_root`, optional required target families, and optional path classifier; returns status, counts, stale paths, missing families, and digests. | Hosts need cheap freshness APIs that also report generated artifact metadata coverage after target layout changes. |
| `OperationConformanceCase`, `ProcessConformanceCase` | Represent operation-level and process-level conformance cases loaded from package-owned fixtures. | Dataclasses hold case identity, contract path, inputs, expected output, and execution metadata used by conformance runners. | Conformance fixtures are public proof anchors for generated package behavior. |
| `load_contract_conformance_case`, `materialize_case_fixture`, `contract_conformance_cases_manifest` | Load, materialize, and enumerate package-owned conformance fixtures. | Helpers use documented fixture JSON shapes and produce stable case/materialization data for runners. | Hosts need stable fixture plumbing to reuse package proofs and map them to downstream evidence. |
| `operation_case_from_contract`, `process_case_from_contract` | Build conformance cases from operation contracts. | Helpers translate contract data into runner-ready operation or process cases using package-owned field semantics. | Case construction should be stable even as private renderer code changes. |
| `CliConformanceTarget`, `CliConformanceResult`, `CliConformanceFailure`, `run_cli_conformance_case` | Run wrapper/process conformance against generated CLIs. | Target/result/failure dataclasses plus runner provide stable subprocess execution, output comparison, and failure reporting semantics. | Hosts need a stable black-box proof path for generated command behavior. |
| `FunctionConformanceTarget`, `FunctionConformanceResult`, `FunctionConformanceFailure`, `run_function_conformance_case` | Run direct Python function conformance against generated callable behavior. | Target/result/failure dataclasses plus runner provide stable callable invocation, expected output comparison, and failure reporting semantics. | Hosts need a stable in-process proof path separate from CLI wrapper behavior. |
| `conformance_ownership_inventory` | Reports ownership metadata for package conformance fixtures. | Returns structured inventory records from packaged proof fixtures. | Downstream evidence and release review need a stable way to distinguish package-owned proof from host-owned proof. |
| `TargetExtensionContract`, `TargetExtensionContractError`, `validate_target_extension_contract`, `target_extension_schema_path` | Define and validate target extension contract data. | Contract dataclass, validation exception, schema path helper, and validator preserve the packaged target-extension schema semantics. | Target extension authors need a stable validation boundary rather than importing internal target modules. |
| `target_support_matrix_entries`, `required_target_proof_matrix_entries`, `missing_target_proof_matrix_entries` | Build and compare target support/proof matrix records. | Helpers produce structured support/proof entries and missing-entry reports from validated target extension contracts and evidence ids. | Host and package CI need stable proof inventory checks for target capabilities. |

## Host Manifest And Primitive Support

`CommandGenerationHostManifest` is the stable host-owned input carrier. Primitive support wiring is explicit:

- `python_primitive_support_path`: optional path to host Python primitive support.
- `typescript_primitive_support_path`: optional path to host TypeScript primitive support.
- `primitive_registry`: optional `PrimitiveRegistry` with host-owned primitive declarations.
- `target_bindings`: optional per-target binding metadata.

The stable contract is support-file discovery and registry metadata, not target-renderer module imports. Hosts should construct `CommandGenerationHostManifest` or pass the equivalent mapping to `render_outputs(...)` and `generate_command_packages(...)`.

## Primitive Registry

`PrimitiveDefinition` and `PrimitiveRegistry` are stable because hosts need durable primitive declaration data. Stable `PrimitiveDefinition` metadata includes `id`, `kind`, `description`, `input_schema_ref`, `output_schema_ref`, `effects`, `target_support`, `owner`, `conformance_refs`, and `unsupported_targets`.

The 1.0 built-in registry uses only:

- `portable`: package-owned generic dataflow, filesystem, parsing, payload assembly, or output mechanics.
- `host-owned`: host-provided runtime bridges such as Python callable or TypeScript domain execution hooks.

Product-shaped transitional compatibility primitives are intentionally absent from the public registry and generated runtime outputs.

## Conformance Runners And Helpers

The stable conformance surface is the package-owned runner/helper set: `CliConformanceTarget`, `CliConformanceResult`, `CliConformanceFailure`, `FunctionConformanceTarget`, `FunctionConformanceResult`, `FunctionConformanceFailure`, `OperationConformanceCase`, `ProcessConformanceCase`, `run_cli_conformance_case`, `run_function_conformance_case`, `operation_case_from_contract`, `process_case_from_contract`, `load_contract_conformance_case`, `materialize_case_fixture`, `contract_conformance_cases_manifest`, and `conformance_ownership_inventory`.

Direct TypeScript function invocation helpers remain available only from their implementation module until they have a stable host-facing contract.

## Generated Artifacts And Freshness

The stable generated-artifact surface is `GeneratedOutput`, `CanonicalCommandArtifact`, `canonical_command_artifacts`, `render_outputs`, `generate_command_packages`, and `generated_output_freshness_report`.

Generated command package resources include `generation_metadata.target.layout_version`. Hosts should inspect generated metadata and freshness reports rather than importing private target renderers. `generated_output_freshness_report(...)` is the stable API for checking rendered output freshness, target-family coverage, stale paths, and expected digests without rewriting files.

## Target Layout And Version Identifiers

Target layout identifiers such as `PYTHON_TARGET_LAYOUT_VERSION` and `TYPESCRIPT_TARGET_LAYOUT_VERSION` are internal constants in target implementation modules. The host-facing stable API is the generated `generation_metadata.target.layout_version` value and the freshness/artifact APIs that expose rendered output state.

Imports from `command_generation.targets.*` are internal target-module imports. They may be useful to package tests, but they are not encouraged or documented as stable public API.

## Semver And Release Notes

Stable public API removals, signature changes, return-shape changes, or semantic changes are compatibility-significant. Package-affecting PRs that change stable API should carry a semver label and release notes explaining the compatibility impact.
