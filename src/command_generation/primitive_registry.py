from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PrimitiveDefinition:
    id: str
    kind: str
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    output_schema: Mapping[str, Any] = field(default_factory=dict)
    effects: Mapping[str, Any] = field(default_factory=dict)
    target_support: Mapping[str, str] = field(default_factory=dict)
    owner: str = "command-generation"
    conformance_refs: tuple[str, ...] = ()
    unsupported_behavior: str = "fail"

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "PrimitiveDefinition":
        primitive_id = str(raw.get("id", "")).strip()
        if not primitive_id:
            raise ValueError("primitive definition id is required")
        refs = raw.get("conformance_refs", ())
        if isinstance(refs, str) or not isinstance(refs, Iterable):
            refs = ()
        return cls(
            id=primitive_id,
            kind=str(raw.get("kind", "portable")).strip() or "portable",
            input_schema=dict(raw.get("input_schema", {})),
            output_schema=dict(raw.get("output_schema", {})),
            effects=dict(raw.get("effects", {})),
            target_support={str(key): str(value) for key, value in dict(raw.get("target_support", {})).items()},
            owner=str(raw.get("owner", "command-generation")),
            conformance_refs=tuple(str(item) for item in refs),
            unsupported_behavior=str(raw.get("unsupported_behavior", "fail")),
        )


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
        support = definition.target_support.get(target, "unsupported")
        if support not in {"implemented", "portable", "host-implemented"}:
            raise ValueError(f"primitive {primitive_id!r} is {support!r} for target {target!r}")
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
                "output_schema": dict(definition.output_schema),
                "effects": dict(definition.effects),
                "target_support": dict(definition.target_support),
                "owner": definition.owner,
                "conformance_refs": list(definition.conformance_refs),
                "unsupported_behavior": definition.unsupported_behavior,
            }
            for definition in sorted(self._definitions.values(), key=lambda item: item.id)
        ]


BUILTIN_PORTABLE_PRIMITIVES = PrimitiveRegistry.from_definitions(
    [
        {"id": "path.target_root.resolve", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "workspace.root.resolve", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "filesystem.exists", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "filesystem.read", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "filesystem.glob", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "json.parse", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "toml.table.counts", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "payload.assemble", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "payload.status", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "payload.lifecycle-plan", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "payload.current-memory", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "payload.verify", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "output.emit", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "output.emit.install-result", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "output.emit.current-memory", "kind": "portable", "target_support": {"python": "implemented", "typescript": "implemented"}},
        {"id": "python.function.call", "kind": "host", "target_support": {"python": "host-implemented", "typescript": "host-implemented"}},
        {"id": "typescript.domain.execute", "kind": "host", "target_support": {"typescript": "host-implemented"}},
    ]
)
