# command-generation

`command-generation` renders command-package artifacts from a host-owned command package IR. It is a maintainer dependency: generated runtimes may contain the rendered outputs, but they do not import this package at runtime.

Public API:

- `load_command_package_ir(path, schema_path=None)` validates IR against the package-owned schema.
- `command_package_schema_path()` returns the packaged JSON schema.
- `render_outputs(manifest, repo_root, source_path, regenerate_command, host_manifest=None)` returns in-memory generated files.
- `generate_command_packages(..., check=True|False)` checks or writes generated files.
- `CommandGenerationHostManifest` declares host roots, custom primitive registry entries, target bindings, and optional host-owned runtime support.
- `PrimitiveRegistry` and `PrimitiveDefinition` describe portable or host-owned primitives with target support.
- `process_case_from_contract(...)`, `CliConformanceTarget`, and `run_cli_conformance_case(...)` provide the generic black-box runner for contract-owned CLI/process conformance cases.
- `operation_case_from_contract(...)`, `FunctionConformanceTarget`, and `run_function_conformance_case(...)` provide the generic JSON-shaped operation conformance runner for direct implementation adapters.
- `contract_conformance_cases_manifest()` and `load_contract_conformance_case(...)` expose package-owned reusable conformance cases.
- `conformance_ownership_inventory()` reports the shared conformance surfaces owned here and the consumer-owned surfaces that should stay out of this package.

Hosts keep product-specific contracts, primitive implementations, and generated output ownership in their own repositories. The package owns generic rendering, schema loading, primitive registry validation, and portable primitive execution helpers.

Conformance strategy:

- Store behavior examples in host-owned contract resources as stable input/expected-output cases.
- Keep target differences in thin adapters such as generated Python functions, generated TypeScript functions, CLI wrappers, or a future MCP adapter.
- Prefer direct function adapters for operation semantics: JSON-shaped inputs should produce normalized result objects or structured errors without depending on argv, stdout, stderr, or shell process behavior.
- Use CLI/process conformance for wrapper boundaries: parser behavior, text projection, exit codes, stderr policy, and fixture state.
- Run the same contract case through the relevant adapter, then compare only the normalized fields that express the behavioral contract.
- Add new one-off tests only for runner internals or target adapter mechanics; command behavior should be represented by contract cases first.

Ownership split:

- This package owns generic conformance machinery, generated-artifact adapter expectations, and reusable behavior cases that apply across consumers.
- Consumers own product-specific operation contracts, runtime primitive implementations, wrapper semantics, integration seams, and proof routing.
- Migration should preserve black-box behavior with smaller reusable cases; it should not copy old regression-test clusters one-for-one.

See `docs/contract-test-replacement-inventory.md` for the current keep/convert/merge/delete inventory.
