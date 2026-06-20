# Transitional Primitive Retirement

`transitional` primitives are package-shipped compatibility adapters for behavior that is not ready to be treated as package-owned portable semantics. They exist to keep existing generated packages working while downstream hosts migrate product-shaped behavior into host-owned registries or generic portable replacements.

Every transitional primitive must declare `transitional_retirement` metadata with:

- `target_end_state`: one of the explicit retirement directions, such as host-owned registry behavior, renamed or reshaped portable behavior, removal after downstream migration, or retained generic behavior with rationale.
- `rationale`: why the primitive is transitional instead of portable or host-owned today.
- `migration_note`: what downstream hosts should move toward.
- `compatibility`: when removal or renaming may be considered.
- `coordination_issue`: the downstream migration issue tracking host-side ordinary-path replacement.
- `inventory_issue`: the downstream proof/check issue that distinguishes ordinary source operation usage from compatibility-only usage.
- `ordinary_usage_gate`: the blocker that prevents package-side deprecation or removal while downstream ordinary source operation IR still references the primitive.
- `package_action_after_migration`: the command-generation-side action that becomes valid after downstream ordinary-path usage is gone.
- `compatibility_fixture_policy`: how any remaining package-side compatibility fixture references must be isolated from ordinary downstream dependence.

New transitional primitives are allowed only when this metadata is present. Missing metadata is a registry error because otherwise transitional behavior can silently become permanent package-owned product semantics.

## Current Inventory

| Primitive | Target end state | Migration note |
| --- | --- | --- |
| `workspace.root.resolve` | renamed/reshaped portable behavior | Prefer `path.target_root.resolve` when repository-root behavior is generic. |
| `payload.status` | host-owned registry behavior | Move installed-payload status policy into an AW-owned primitive. |
| `payload.lifecycle-plan` | host-owned registry behavior | Move lifecycle-plan construction into an AW-owned primitive. |
| `payload.current-memory` | host-owned registry behavior | Move current-memory selection and rendering into an AW-owned primitive. |
| `payload.verify` | host-owned registry behavior | Move installed-payload verification into an AW-owned primitive. |
| `output.emit.install-result` | removed after downstream migration | Use `output.emit` for generic output and an AW-owned formatter for AW text. |
| `output.emit.current-memory` | removed after downstream migration | Use `output.emit` for generic output and an AW-owned formatter for AW text. |

The AW ordinary-path migration gate is [agentic-workspace#1638](https://github.com/rickardvh/agentic-workspace/issues/1638), and the AW inventory/proof gate is [agentic-workspace#1639](https://github.com/rickardvh/agentic-workspace/issues/1639). Command-generation issue [#44](https://github.com/rickardvh/command-generation/issues/44) owns this package-side coordination policy.

## Package-Side Gate

Command-generation must not deprecate, remove, or reclassify these transitional primitives while AW ordinary source operation IR still depends on their command-generation IDs. AW must first replace ordinary source operation use through AW-owned primitive IDs or host-neutral replacements, and its inventory must prove zero ordinary source-operation usage.

Once that downstream gate is satisfied, the package-side action is to classify the affected primitives as compatibility-only/deprecated, keep only explicitly isolated compatibility fixtures if needed, announce the change as compatibility-significant, and remove or replace the package primitives in a release that documents the migration path.

Compatibility fixture use inside command-generation is not ordinary downstream dependence. Any remaining fixture reference must be path-isolated and labeled as legacy compatibility coverage.

## Compatibility Sequence

Removal or renaming should follow this sequence:

1. Keep the transitional primitive implemented while generated packages still reference it.
2. Track AW ordinary-path replacement in [agentic-workspace#1638](https://github.com/rickardvh/agentic-workspace/issues/1638).
3. Prove zero AW ordinary source-operation usage in [agentic-workspace#1639](https://github.com/rickardvh/agentic-workspace/issues/1639), with any remaining use compatibility-test-only.
4. Classify remaining package references as compatibility-only/deprecated and keep them isolated from ordinary downstream dependence.
5. Announce the removal or rename in release notes as compatibility-significant.
6. Remove or replace the package primitive only after the downstream migration path exists and the ordinary-usage gate is satisfied.

This package must not promote AW-specific installed-payload or current-memory behavior back into portable primitive semantics without a documented generic rationale.
