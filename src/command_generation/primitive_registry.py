from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PrimitiveDefinition:
    id: str
    kind: str
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    input_schema_ref: str = ""
    output_schema: Mapping[str, Any] = field(default_factory=dict)
    output_schema_ref: str = ""
    effects: Mapping[str, Any] = field(default_factory=dict)
    target_support: Mapping[str, str] = field(default_factory=dict)
    owner: str = "command-generation"
    description: str = ""
    conformance_refs: tuple[str, ...] = ()
    unsupported_behavior: str = "fail"
    unsupported_targets: Mapping[str, str] = field(default_factory=dict)
    transitional_retirement: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "PrimitiveDefinition":
        primitive_id = str(raw.get("id", "")).strip()
        if not primitive_id:
            raise ValueError("primitive definition id is required")

        def object_field(name: str) -> dict[str, Any]:
            value = raw.get(name, {})
            return dict(value) if isinstance(value, Mapping) else {}

        refs = raw.get("conformance_refs", ())
        if isinstance(refs, str) or not isinstance(refs, Iterable):
            refs = ()
        singular_ref = str(raw.get("conformance_ref", "")).strip()
        normalized_refs = [str(item) for item in refs if str(item).strip()]
        if singular_ref and singular_ref not in normalized_refs:
            normalized_refs.append(singular_ref)
        raw_kind = str(raw.get("kind", "portable")).strip() or "portable"
        kind_aliases = {"host": "host-owned"}
        normalized_kind = kind_aliases.get(raw_kind, raw_kind)
        transitional_retirement = object_field("transitional_retirement")
        if normalized_kind == "transitional":
            _validate_transitional_retirement(
                primitive_id,
                owner=str(raw.get("owner", "command-generation")),
                retirement=transitional_retirement,
            )
        return cls(
            id=primitive_id,
            kind=normalized_kind,
            input_schema=object_field("input_schema"),
            input_schema_ref=str(raw.get("input_schema_ref", "")).strip(),
            output_schema=object_field("output_schema"),
            output_schema_ref=str(raw.get("output_schema_ref", "")).strip(),
            effects=object_field("effects"),
            target_support={str(key): str(value) for key, value in object_field("target_support").items()},
            owner=str(raw.get("owner", "command-generation")),
            description=str(raw.get("description", raw.get("summary", ""))).strip(),
            conformance_refs=tuple(normalized_refs),
            unsupported_behavior=str(raw.get("unsupported_behavior", "fail")),
            unsupported_targets={str(key): str(value) for key, value in object_field("unsupported_targets").items()},
            transitional_retirement=transitional_retirement,
        )

    def support_for(self, target: str) -> str:
        return self.target_support.get(target, "unsupported")

    def unsupported_reason(self, target: str) -> str:
        return self.unsupported_targets.get(target) or self.unsupported_behavior


class PrimitiveRegistry:
    def __init__(self, definitions: Iterable[PrimitiveDefinition] = ()) -> None:
        self._definitions = {definition.id: definition for definition in definitions}

    @classmethod
    def from_definitions(cls, raw_definitions: Iterable[Mapping[str, Any]]) -> "PrimitiveRegistry":
        return cls(PrimitiveDefinition.from_mapping(raw) for raw in raw_definitions)

    def definition(self, primitive_id: str) -> PrimitiveDefinition | None:
        return self._definitions.get(primitive_id)

    def require_declared(self, primitive_id: str) -> PrimitiveDefinition:
        definition = self.definition(primitive_id)
        if definition is None:
            raise ValueError(f"primitive is not declared in host registry: {primitive_id}")
        return definition

    def ensure_supported(self, primitive_id: str, target: str) -> PrimitiveDefinition:
        definition = self.require_declared(primitive_id)
        support = definition.support_for(target)
        if support not in {"implemented", "portable", "host-implemented"}:
            reason = definition.unsupported_reason(target)
            raise ValueError(f"primitive {primitive_id!r} is {support!r} for target {target!r}: {reason}")
        return definition

    def ids(self) -> set[str]:
        return set(self._definitions)

    def merge(self, other: "PrimitiveRegistry") -> "PrimitiveRegistry":
        return PrimitiveRegistry([*self._definitions.values(), *other._definitions.values()])

    def to_jsonable(self) -> list[dict[str, Any]]:
        return [
            {
                "id": definition.id,
                "kind": definition.kind,
                "input_schema": dict(definition.input_schema),
                "input_schema_ref": definition.input_schema_ref,
                "output_schema": dict(definition.output_schema),
                "output_schema_ref": definition.output_schema_ref,
                "effects": dict(definition.effects),
                "target_support": dict(definition.target_support),
                "owner": definition.owner,
                "description": definition.description,
                "conformance_refs": list(definition.conformance_refs),
                "unsupported_behavior": definition.unsupported_behavior,
                "unsupported_targets": dict(definition.unsupported_targets),
                "transitional_retirement": dict(definition.transitional_retirement),
            }
            for definition in sorted(self._definitions.values(), key=lambda item: item.id)
        ]


def _validate_transitional_retirement(primitive_id: str, *, owner: str, retirement: Mapping[str, Any]) -> None:
    if owner == "command-generation":
        raise ValueError(f"transitional primitive {primitive_id!r} must declare the host or migration owner")
    required = {
        "target_end_state",
        "rationale",
        "migration_note",
        "compatibility",
        "coordination_issue",
        "inventory_issue",
        "ordinary_usage_gate",
        "package_action_after_migration",
        "compatibility_fixture_policy",
    }
    missing = sorted(field for field in required if not str(retirement.get(field, "")).strip())
    if missing:
        raise ValueError(
            f"transitional primitive {primitive_id!r} must declare transitional_retirement fields: {', '.join(missing)}"
        )


_DOWNSTREAM_TRANSITIONAL_MIGRATION_REF = "downstream-ordinary-path-migration"
_DOWNSTREAM_TRANSITIONAL_INVENTORY_REF = "downstream-ordinary-usage-proof"


def _aw_transitional_retirement(
    *,
    primitive_id: str,
    target_end_state: str,
    rationale: str,
    migration_note: str,
    compatibility: str,
) -> dict[str, str]:
    return {
        "target_end_state": target_end_state,
        "rationale": rationale,
        "migration_note": migration_note,
        "compatibility": compatibility,
        "coordination_issue": _DOWNSTREAM_TRANSITIONAL_MIGRATION_REF,
        "inventory_issue": _DOWNSTREAM_TRANSITIONAL_INVENTORY_REF,
        "ordinary_usage_gate": (
            f"Do not deprecate or remove {primitive_id} while downstream ordinary source operation IR references it; "
            f"{_DOWNSTREAM_TRANSITIONAL_INVENTORY_REF} must prove zero ordinary source-operation usage."
        ),
        "package_action_after_migration": (
            f"After downstream ordinary-path usage is gone, classify {primitive_id} as compatibility-only/deprecated, "
            "keep only explicitly isolated compatibility fixtures, and remove or replace it in a compatibility-significant release."
        ),
        "compatibility_fixture_policy": (
            "Remaining command-generation fixture usage must be compatibility-test-only, path-isolated, "
            "and not treated as ordinary downstream dependence."
        ),
    }


BUILTIN_PORTABLE_PRIMITIVES = PrimitiveRegistry.from_definitions(
    [
        {
            "id": "path.target_root.resolve",
            "kind": "portable",
            "description": "Resolve a caller-supplied target path under the execution working directory.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
        },
        {
            "id": "workspace.root.resolve",
            "kind": "transitional",
            "owner": "host",
            "description": "Legacy workspace-shaped root resolver retained for existing generated packages.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
            "transitional_retirement": _aw_transitional_retirement(
                primitive_id="workspace.root.resolve",
                target_end_state="renamed/reshaped portable behavior",
                rationale="Existing workspace-shaped manifests use a workspace-named root resolver, but the generic behavior is target path resolution.",
                migration_note="Migrate host manifests to path.target_root.resolve where repository-root semantics are not product-specific.",
                compatibility="Retain until downstream generated packages no longer reference workspace.root.resolve.",
            ),
        },
        {
            "id": "filesystem.exists",
            "kind": "portable",
            "description": "Check for a file or directory under a declared primitive root.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
        },
        {
            "id": "filesystem.read",
            "kind": "portable",
            "description": "Read UTF-8 text from a declared primitive root.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
        },
        {
            "id": "filesystem.glob",
            "kind": "portable",
            "description": "List paths under a declared primitive root.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
        },
        {
            "id": "json.parse",
            "kind": "portable",
            "description": "Parse JSON text from operation values.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
        },
        {
            "id": "toml.table.counts",
            "kind": "portable",
            "description": "Count TOML table rows by status-like fields without host-specific policy.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
        },
        {
            "id": "payload.assemble",
            "kind": "portable",
            "description": "Assemble generic file, skill, template, or package-file-list payloads.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
        },
        {
            "id": "payload.status",
            "kind": "transitional",
            "owner": "host",
            "description": "Installed-payload status policy retained for existing host-style package manifests.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
            "transitional_retirement": _aw_transitional_retirement(
                primitive_id="payload.status",
                target_end_state="host-owned registry behavior",
                rationale="Installed-payload status rules are host product policy, not generic command-generation payload assembly.",
                migration_note="Move status policy into a host-owned primitive registry/runtime implementation.",
                compatibility="Retain until downstream manifests have migrated and package release notes announce removal or replacement.",
            ),
        },
        {
            "id": "payload.lifecycle-plan",
            "kind": "transitional",
            "owner": "host",
            "description": "Installed-payload lifecycle policy retained for existing host-style package manifests.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
            "transitional_retirement": _aw_transitional_retirement(
                primitive_id="payload.lifecycle-plan",
                target_end_state="host-owned registry behavior",
                rationale="Lifecycle-plan interpretation is host package lifecycle policy rather than reusable payload mechanics.",
                migration_note="Move lifecycle-plan construction into a host-owned primitive registry/runtime implementation.",
                compatibility="Retain until downstream manifests have migrated and package release notes announce removal or replacement.",
            ),
        },
        {
            "id": "payload.current-memory",
            "kind": "transitional",
            "owner": "host",
            "description": "Current-memory payload policy retained for existing host-style package manifests.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
            "transitional_retirement": _aw_transitional_retirement(
                primitive_id="payload.current-memory",
                target_end_state="host-owned registry behavior",
                rationale="Current-memory views are host memory product policy, not a generic command-generation primitive.",
                migration_note="Move current-memory selection and rendering into a host-owned primitive registry/runtime implementation.",
                compatibility="Retain until downstream manifests have migrated and package release notes announce removal or replacement.",
            ),
        },
        {
            "id": "payload.verify",
            "kind": "transitional",
            "owner": "host",
            "description": "Installed-payload verification policy retained for existing host-style package manifests.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
            "transitional_retirement": _aw_transitional_retirement(
                primitive_id="payload.verify",
                target_end_state="host-owned registry behavior",
                rationale="Installed-payload verification checks encode host compatibility and package policy.",
                migration_note="Move verification policy into a host-owned primitive registry/runtime implementation.",
                compatibility="Retain until downstream manifests have migrated and package release notes announce removal or replacement.",
            ),
        },
        {
            "id": "output.emit",
            "kind": "portable",
            "description": "Emit JSON or compact text from a result payload.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
        },
        {
            "id": "output.emit.install-result",
            "kind": "transitional",
            "owner": "host",
            "description": "Installed-payload text projection retained for existing host-style package manifests.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
            "transitional_retirement": _aw_transitional_retirement(
                primitive_id="output.emit.install-result",
                target_end_state="removed after downstream migration",
                rationale="Install-result text projection is coupled to host installed-payload output shape.",
                migration_note="Migrate generic output to output.emit and host-specific text to a host-owned formatter primitive.",
                compatibility="Retain until downstream manifests have migrated and package release notes announce removal or replacement.",
            ),
        },
        {
            "id": "output.emit.current-memory",
            "kind": "transitional",
            "owner": "host",
            "description": "Current-memory text projection retained for existing host-style package manifests.",
            "target_support": {"python": "implemented", "typescript": "implemented"},
            "transitional_retirement": _aw_transitional_retirement(
                primitive_id="output.emit.current-memory",
                target_end_state="removed after downstream migration",
                rationale="Current-memory text projection is coupled to host memory output shape.",
                migration_note="Migrate generic output to output.emit and host-specific text to a host-owned formatter primitive.",
                compatibility="Retain until downstream manifests have migrated and package release notes announce removal or replacement.",
            ),
        },
        {
            "id": "python.function.call",
            "kind": "host-owned",
            "description": "Host-provided Python callable bridge.",
            "target_support": {"python": "host-implemented", "typescript": "host-implemented"},
        },
        {
            "id": "typescript.domain.execute",
            "kind": "host-owned",
            "description": "Host-provided TypeScript domain runtime bridge.",
            "target_support": {"typescript": "host-implemented"},
        },
    ]
)
