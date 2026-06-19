from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from command_generation.primitive_registry import PrimitiveRegistry


@dataclass(frozen=True)
class CommandGenerationHostManifest:
    """Host-owned inputs that keep product knowledge out of generic generation code."""

    generated_root: Path | None = None
    package_ids: tuple[str, ...] = ()
    contract_roots: Mapping[str, Path] = field(default_factory=dict)
    primitive_registry: PrimitiveRegistry | None = None
    target_bindings: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    python_primitive_executor_path: Path | None = None
    typescript_runtime_support_path: Path | None = None
    operation_schema_version: str = "command-generation/operation/v1"

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, Any] | "CommandGenerationHostManifest" | None,
        *,
        repo_root: Path | None = None,
    ) -> "CommandGenerationHostManifest":
        if raw is None:
            return cls()
        if isinstance(raw, CommandGenerationHostManifest):
            return raw
        root = repo_root or Path.cwd()

        def _path(value: Any) -> Path | None:
            if value in (None, ""):
                return None
            candidate = Path(str(value))
            return candidate if candidate.is_absolute() else root / candidate

        contract_roots = {
            str(key): path
            for key, value in dict(raw.get("contract_roots", {})).items()
            if (path := _path(value)) is not None
        }
        registry_raw = raw.get("primitive_registry")
        registry = (
            registry_raw
            if isinstance(registry_raw, PrimitiveRegistry)
            else PrimitiveRegistry.from_definitions(registry_raw or [])
        )
        package_ids = raw.get("package_ids", ())
        if isinstance(package_ids, Sequence) and not isinstance(package_ids, (str, bytes)):
            normalized_package_ids = tuple(str(item) for item in package_ids)
        else:
            normalized_package_ids = ()
        target_bindings = {
            str(key): value
            for key, value in dict(raw.get("target_bindings", {})).items()
            if isinstance(value, Mapping)
        }
        return cls(
            generated_root=_path(raw.get("generated_root")),
            package_ids=normalized_package_ids,
            contract_roots=contract_roots,
            primitive_registry=registry,
            target_bindings=target_bindings,
            python_primitive_executor_path=_path(raw.get("python_primitive_executor_path")),
            typescript_runtime_support_path=_path(raw.get("typescript_runtime_support_path")),
            operation_schema_version=str(raw.get("operation_schema_version") or "command-generation/operation/v1"),
        )
