from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from command_generation.host_manifest import CommandGenerationHostManifest
from command_generation.operation_composition import expand_operation_steps, operation_fragments
from command_generation.primitive_registry import BUILTIN_PORTABLE_PRIMITIVES, PrimitiveRegistry


@dataclass(frozen=True)
class GeneratedOutput:
    path: Path
    content: str


def _json_block(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _maturity_levels(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    policy = manifest["generation_policy"]["generated_package_maturity"]
    return {level["id"]: level for level in policy["levels"]}


def _is_runnable_typescript_target(target: dict[str, Any]) -> bool:
    return target.get("maturity_level_ref") in {
        "runnable-read-only-adapter",
        "runtime-backed-read-only-adapter",
        "weak-agent-safe-adapter",
        "mutation-capable-adapter",
    }


def _is_weak_agent_safe_typescript_target(target: dict[str, Any]) -> bool:
    return target.get("maturity_level_ref") == "weak-agent-safe-adapter"


def _is_weak_agent_safe_python_target(target: dict[str, Any]) -> bool:
    return target.get("kind") == "python" and target.get("maturity_level_ref") == "weak-agent-safe-adapter"


def _is_runtime_backed_python_target(target: dict[str, Any]) -> bool:
    return target.get("kind") == "python" and target.get("maturity_level_ref") in {
        "runtime-backed-read-only-adapter",
        "weak-agent-safe-adapter",
        "mutation-capable-adapter",
    }


def _weak_agent_routing_for_target(target: dict[str, Any], maturity_levels: dict[str, dict[str, Any]]) -> str:
    maturity = maturity_levels[str(target["maturity_level_ref"])]
    return str(maturity["weak_agent_routing"])


def _runtime_command_for_package(package: dict[str, Any], runtime_binding: dict[str, Any]) -> str:
    python_runtime_binding = package.get("python_runtime_binding", {})
    if isinstance(python_runtime_binding, dict) and python_runtime_binding.get("default_runtime_command"):
        return str(python_runtime_binding["default_runtime_command"])
    return str(runtime_binding["default_runtime_command"])


def _runtime_module_file_for_package(package: dict[str, Any]) -> str:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return ""
    configured = str(binding.get("runtime_module_file") or "")
    return configured.removesuffix(".py")


def _version_metadata_for_package(package: dict[str, Any]) -> dict[str, Any]:
    metadata = package.get("version_metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _version_fallback_for_package(package: dict[str, Any]) -> str:
    return str(_version_metadata_for_package(package).get("fallback_version") or "0.0.0")


def _operation_executor_binding(package: dict[str, Any]) -> dict[str, Any]:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return {}
    operation_executor = binding.get("operation_executor", {})
    return operation_executor if isinstance(operation_executor, dict) else {}


def _local_runtime_bindings(package: dict[str, Any]) -> list[dict[str, Any]]:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return []
    return [item for item in binding.get("local_runtime_bindings", []) if isinstance(item, dict)]


def _python_resource_copies(package: dict[str, Any]) -> list[dict[str, Any]]:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return []
    return [item for item in binding.get("resource_copies", []) if isinstance(item, dict)]


def _resource_copy_source_files(source_root: Path) -> list[Path]:
    return sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.relative_to(source_root).parts
        and path.suffix not in {".pyc", ".pyo"}
    )


def _local_runtime_binding_for_import(package: dict[str, Any], import_module: str) -> dict[str, Any] | None:
    for binding in _local_runtime_bindings(package):
        if str(binding.get("source_import_module") or "") == import_module:
            return binding
    return None


def _command_module_import_for_binding(binding: dict[str, Any]) -> str:
    return f"..{str(binding['module_file'])}"


def _operation_executor_import_for_binding(binding: dict[str, Any]) -> str:
    module_file = str(binding["module_file"])
    if module_file.startswith("primitives."):
        return f".{module_file.removeprefix('primitives.')}"
    return f"..{module_file}"


def _python_adapter_commands(package: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        command for command in package["commands"] if command.get("status") == "generated" and isinstance(command.get("interface"), dict)
    ]


def _interface_operation_refs(interface: dict[str, Any], inherited_operation_ref: dict[str, Any]) -> list[dict[str, Any]]:
    operation_ref = interface.get("operation_ref", inherited_operation_ref)
    current_operation_ref = operation_ref if isinstance(operation_ref, dict) else inherited_operation_ref
    refs = [current_operation_ref]
    for subcommand in interface.get("subcommands", []):
        if isinstance(subcommand, dict):
            refs.extend(_interface_operation_refs(subcommand, current_operation_ref))
    return refs


def _command_operation_refs(command: dict[str, Any]) -> list[dict[str, Any]]:
    operation_ref = command.get("operation_ref", {})
    interface = command.get("interface", {})
    if not isinstance(operation_ref, dict):
        return []
    if not isinstance(interface, dict):
        return [operation_ref]
    return _interface_operation_refs(interface, operation_ref)


def _python_adapter_command_payload(package: dict[str, Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for command in _python_adapter_commands(package):
        interface = dict(command["interface"])
        operation_ref = dict(command["operation_ref"])
        payload.append(
            {
                "adapter_id": command["adapter_id"],
                "operation_id": operation_ref["id"],
                "operation_path": operation_ref["path"],
                "interface": interface,
            }
        )
    return payload


def _typescript_minimal_operation(*, operation_id: str, schema_version: str = "command-generation/operation/v1") -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "id": operation_id,
        "summary": "Generated TypeScript native operation binding.",
        "migration_status": "generated-typescript-native",
    }


def _operation_for_ref(package: dict[str, Any], operation_ref: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    operation_path = str(operation_ref.get("path", ""))
    operation_id = str(operation_ref.get("id", ""))
    operation_contract_root = repo_root / str(package["operation_contract_root"])
    source = operation_contract_root / operation_path
    if source.is_file():
        return json.loads(source.read_text(encoding="utf-8"))
    if operation_id:
        return _typescript_minimal_operation(operation_id=operation_id)
    return {}


def _registry_for_host(host_manifest: CommandGenerationHostManifest) -> PrimitiveRegistry | None:
    if host_manifest.primitive_registry is None:
        return None
    return BUILTIN_PORTABLE_PRIMITIVES.merge(host_manifest.primitive_registry)


def _validate_target_primitive_support(
    package: dict[str, Any],
    target: dict[str, Any],
    *,
    repo_root: Path,
    host_manifest: CommandGenerationHostManifest,
) -> None:
    registry = _registry_for_host(host_manifest)
    if registry is None:
        return
    target_kind = str(target.get("kind", ""))
    if target_kind not in {"python", "typescript"}:
        return
    errors: list[str] = []
    for command in _python_adapter_commands(package):
        for operation_ref in _command_operation_refs(command):
            operation = _operation_for_ref(package, operation_ref, repo_root=repo_root)
            for step in _operation_ir_primitive_steps(operation):
                primitive_id = str(step.get("uses", ""))
                try:
                    registry.ensure_supported(primitive_id, target_kind)
                except ValueError as exc:
                    errors.append(f"{package.get('id')}:{operation.get('id')}:{primitive_id}: {exc}")
    if errors:
        raise ValueError("unsupported command-generation primitive target support:\n" + "\n".join(errors))


def _operation_ir_primitive_steps(operation: dict[str, Any]) -> list[dict[str, Any]]:
    ir_plan = operation.get("ir_plan", {})
    if not isinstance(ir_plan, dict):
        return []
    steps = ir_plan.get("steps", [])
    if not isinstance(steps, list):
        return []
    fragments = operation_fragments(operation, error_type=ValueError)
    return expand_operation_steps(steps, fragments=fragments, error_type=ValueError)

