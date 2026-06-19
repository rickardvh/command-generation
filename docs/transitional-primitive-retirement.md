# Transitional Primitive Retirement

`transitional` primitives are package-shipped compatibility adapters for behavior that is not ready to be treated as package-owned portable semantics. They exist to keep existing generated packages working while downstream hosts migrate product-shaped behavior into host-owned registries or generic portable replacements.

Every transitional primitive must declare `transitional_retirement` metadata with:

- `target_end_state`: one of the explicit retirement directions, such as host-owned registry behavior, renamed or reshaped portable behavior, removal after downstream migration, or retained generic behavior with rationale.
- `rationale`: why the primitive is transitional instead of portable or host-owned today.
- `migration_note`: what downstream hosts should move toward.
- `compatibility`: when removal or renaming may be considered.
- `coordination_issue`: the downstream migration issue tracking host-side work.

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

The host-side migration coordination issue is [#44](https://github.com/rickardvh/command-generation/issues/44).

## Compatibility Sequence

Removal or renaming should follow this sequence:

1. Keep the transitional primitive implemented while generated packages still reference it.
2. Add or use host-owned registry behavior, or a generic portable replacement, in downstream manifests.
3. Prove downstream generated packages no longer reference the transitional primitive.
4. Announce the removal or rename in release notes as compatibility-significant.
5. Remove or replace the package primitive only after the downstream migration path exists.

This package must not promote AW-specific installed-payload or current-memory behavior back into portable primitive semantics without a documented generic rationale.
