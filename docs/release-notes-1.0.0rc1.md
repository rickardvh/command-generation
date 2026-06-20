# command-generation 1.0.0rc1 Release Notes

`command-generation` 1.0.0rc1 is the first release candidate for the stable host-facing generation API.

## Compatibility-Significant Changes

- Removed the AW-shaped transitional primitive compatibility IDs from the built-in registry and ordinary generated runtime surface:
  - `workspace.root.resolve`
  - `payload.status`
  - `payload.lifecycle-plan`
  - `payload.current-memory`
  - `payload.verify`
  - `output.emit.install-result`
  - `output.emit.current-memory`
- Pruned package-level `command_generation.__all__` to stable 1.0 APIs only.
- Removed package-level exports for runtime executor plumbing and direct TypeScript function invocation helpers. Those implementation helpers remain importable from their implementation modules when package tests or experimental target work need them.

## Stable Public API Boundary

The stable package-level API is documented in `docs/public-api.md`. It covers:

- command package IR loading and schema lookup;
- host manifest and primitive registry metadata;
- generated output rendering, writing/checking, freshness, and canonical artifact records;
- CLI/process and Python function conformance runners;
- target extension contract validation and proof matrix helpers.

## Generated Runtime Boundary

Generated Python and TypeScript packages remain self-contained at runtime. The generator renders primitive executor shells, operation execution, command adapters, resources, and package metadata; generated runtimes do not import `command_generation`.

## Host-Owned Primitive Extension Model

Hosts extend generated runtimes through:

- `CommandGenerationHostManifest.primitive_registry`;
- `python_primitive_support_path`;
- `typescript_primitive_support_path`;
- explicit host-owned primitive IDs with target support metadata.

Product-specific behavior belongs in host-owned primitive support modules or host operation contracts, not in command-generation built-ins.

## Release Candidate Proof

Before tagging 1.0, run:

```powershell
uv run pytest
uv run ruff check src tests scripts
uv build
uv run python scripts/prove_aw_artifact_consumption.py --aw-root ../agentic-workspace --expected-version 1.0.0rc1
```

The artifact-consumption proof installs the built wheel in an isolated environment, fails if `command_generation` resolves to the source tree, and runs AW generated-command generation, static proof, primitive ownership proof, and operation conformance.
