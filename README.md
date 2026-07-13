# command-generation

`command-generation` renders command-package artifacts from a host-owned command package IR. It is a maintainer dependency: generated runtimes may contain the rendered outputs, but they do not import this package at runtime.

The package exists to keep command surface generation, reusable conformance runners, and portable primitive machinery in one generic library while leaving product semantics in host repositories.

## What It Owns

`command-generation` owns:

- the command package IR schema and schema loader;
- deterministic renderers for generated Python and TypeScript command-package artifacts;
- generated-artifact freshness accounting;
- generic portable primitive execution helpers;
- reusable CLI/process and function/operation conformance runners;
- package-owned fixture cases that exercise generic adapter behavior.

Host repositories own:

- product-specific operation contracts and generated output ownership;
- host runtime primitive implementations and integration seams;
- wrapper policy, installed-payload policy, and proof routing;
- release pinning and compatibility policy for their generated artifacts.

Generated runtimes should be self-contained with respect to this package. If a generated CLI/function package imports `command_generation` at runtime, that is a boundary violation.

## Primitive Ownership

Built-in primitive definitions carry a `kind` classification:

- `portable`: package-owned generic dataflow, filesystem, parsing, payload assembly, or output mechanics.
- `host-owned`: host-provided runtime bridges such as Python callable or TypeScript domain execution hooks.

The exported `BUILTIN_PORTABLE_PRIMITIVES` registry contains package-owned portable primitives plus the explicit host-owned bridge IDs that generated runtimes may call when the host supplies support modules. It does not carry product-shaped transitional compatibility primitives.

`payload.project` is the generic projection primitive for exact dot-path selected-output wrappers. See [Projection primitives](docs/projection-primitives.md) for its ownership boundary.

`output.emit` is the generic JSON/text emission primitive. Declared `text_views` provide portable compact text rendering with scalar matching, scalar placeholders, list-of-scalar `join`, JSON-domain truthiness, iteration, and explicit JSON blocks for structured values. See [`output.emit` text views](docs/output-emit-text-views.md) for the rendering language and failure behavior.

## Public API

- `load_command_package_ir(path, schema_path=None)` validates IR against the package-owned schema.
- `command_package_schema_path()` returns the packaged JSON schema.
- `render_outputs(manifest, repo_root, source_path, regenerate_command, host_manifest=None)` returns in-memory generated files.
- `generate_command_packages(..., check=True|False)` checks or writes generated files.
- `CommandGenerationHostManifest` declares host roots, custom primitive registry entries, target bindings, and optional host-owned primitive support.
- `PrimitiveRegistry` and `PrimitiveDefinition` describe portable or host-owned primitives with target support.
- `TargetExtensionContract`, `validate_target_extension_contract(...)`, and `target_support_matrix_entries(...)` define how new generated targets declare projection rules, runtime dependencies, callable/wrapper shape, packaging, conformance execution, and matrix support without owning product semantics.
- `process_case_from_contract(...)`, `CliConformanceTarget`, and `run_cli_conformance_case(...)` provide the generic black-box runner for contract-owned CLI/process conformance cases.
- `operation_case_from_contract(...)`, `FunctionConformanceTarget`, and `run_function_conformance_case(...)` provide the generic JSON-shaped operation conformance runner for direct Python implementation adapters without CLI argv semantics.
- `contract_conformance_cases_manifest()` and `load_contract_conformance_case(...)` expose package-owned reusable conformance cases.
- `conformance_ownership_inventory()` reports the shared conformance surfaces owned here and the consumer-owned surfaces that should stay out of this package.

See [Public API Classification](docs/public-api.md) for the stable `command_generation.__all__` export set.

Host-owned primitive support is intentionally narrower than target executor replacement. `command-generation` renders the Python primitive executor skeleton, TypeScript runtime shell, and built-in portable primitive dispatch. Hosts may provide `python_primitive_support_path` or `typescript_primitive_support_path` modules that export only domain-runtime primitive behavior through `execute_host_primitive(...)` or `executeHostPrimitive(...)`; hosts do not replace the generated target shell. Unsupported host/domain primitive IDs fail explicitly at registry validation or runtime dispatch, and generated runtimes remain self-contained after rendering.

## Command Package IR

Host repositories provide command package manifests that describe commands, operation refs, target projections, runtime bindings, resource copies, maturity policy, and generated output locations. This package validates and renders those manifests, but the manifest remains host-owned.

The canonical command package IR schema version is `command-generation/command-package-ir/v1`. The loader accepts the legacy `agentic-workspace/command-package-ir/v1` value as a transitional alias and returns the canonical command-generation value after loading.

The IR should express stable command and operation intent. Target renderers may project that intent into Python modules, TypeScript modules, CLI adapters, or future adapter surfaces. Generated files are outputs, not the source of truth.

## Operation Callables And Wrappers

Direct function adapters should be operation-shaped semantic artifacts. Their input values are operation value names, not CLI argument names. CLI/process adapters remain wrapper surfaces and may map flags or parser arguments onto operation values.

That split matters for conformance:

- use function conformance for JSON-shaped operation semantics;
- use process conformance for parser behavior, stdout/stderr, exit codes, and wrapper state;
- do not let a CLI flag name become the semantic contract unless the operation input is intentionally named the same way.

## Target Extension Contract

Target implementations are declared with `command-generation/target-extension/v1`. The contract records target identity, projection rules, runtime dependency boundaries, direct operation callable shape, wrapper/adapter responsibilities, packaging layout, conformance execution, and support-declaration rules for matrix inclusion.

Targets must not own product operation semantics or require per-operation feature maintenance. Ordinary behavior remains in host-owned operation IR, primitive refs, schemas, and input/output/error cases. Target maintenance is limited to runtime dependency updates, target compatibility work, and projection/runtime-adapter bugs.

Generated target resources are target-scoped. A TypeScript package resource carries universal command and operation metadata plus the TypeScript target declaration, but it does not ship Python runtime binding details as executable fallback metadata. Target-irrelevant runtime bindings stay in the host IR and in the target that actually owns them.

Generated package resources carry `generation_metadata` with the `command-generation` package version, source IR schema version, target kind, target package name, and target layout version. Hosts can compare that metadata against their pinned generator version without importing `command_generation` from generated runtimes.

`render_outputs(...)` records the manifest schema version it is given. Hosts that need canonical provenance should load manifests through `load_command_package_ir(...)` first so legacy schema aliases are normalized before rendering.

See [Generated Target Layout Compatibility](docs/target-layout-compatibility.md) for the meaning of target layout versions and when they must change.

## Conformance Strategy

- Store behavior examples in host-owned contract resources as stable input/expected-output cases.
- Keep target differences in thin adapters such as generated Python functions, generated TypeScript functions, CLI wrappers, or a future MCP adapter.
- Prefer direct function adapters for operation semantics: JSON-shaped inputs should produce normalized result objects or structured errors without depending on argv, stdout, stderr, or shell process behavior.
- Use CLI/process conformance for wrapper boundaries: parser behavior, text projection, exit codes, stderr policy, and fixture state.
- Use the [target proof matrix](docs/target-proof-matrix.md) to keep implemented target support tied to direct operation, CLI/process, freshness, runtime-boundary, and primitive-support evidence.
- Run the same contract case through the relevant adapter, then compare only the normalized fields that express the behavioral contract.
- Add new one-off tests only for runner internals or target adapter mechanics; command behavior should be represented by contract cases first.

See `docs/contract-test-replacement-inventory.md` for the current keep/convert/merge/delete inventory.

## Development

Install dependencies with `uv` and run the focused tests for the surface you changed:

```powershell
uv run pytest
uv run ruff check src tests
```

Useful focused commands:

```powershell
uv run pytest tests/test_public_api.py -q
uv run pytest tests/test_primitive_executor.py -q
uv run python tests/primitive_conformance.py
```
