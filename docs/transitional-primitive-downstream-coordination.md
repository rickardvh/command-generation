# Transitional Primitive Downstream Coordination

This file is a temporary coordination-only record. It is not generated runtime behavior, exported primitive registry semantics, or a host product contract.

## Current Downstream Proof

The current downstream host proof for removing Agentic Workspace-specific ordinary-path dependence is tracked in:

- `rickardvh/agentic-workspace#1645`

Use this command in the downstream repository to prove the gate:

```bash
uv run python scripts/check/check_generated_command_packages.py --aw-primitive-ownership --format json
```

The report must prove:

- ordinary downstream source operation IR has zero command-generation transitional primitive ID usage;
- downstream-owned primitive declarations and runtime references are present;
- generated artifacts are fresh;
- remaining legacy IDs are isolated to explicit compatibility checker or test paths.

## CG Boundary

`command-generation` should refer to this class of proof through provider-neutral registry fields such as `downstream-ordinary-path-migration` and `downstream-ordinary-usage-proof`. Concrete downstream issue URLs and commands belong in this coordination record until the transitional primitives are removed or the coordination gate is no longer needed.
