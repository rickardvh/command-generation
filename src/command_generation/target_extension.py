from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REQUIRED_TARGET_PROOF_KINDS: tuple[dict[str, str], ...] = (
    {
        "proof_kind": "direct-operation-success",
        "surface": "function",
        "applies_when": "operation callable adapter is declared",
    },
    {
        "proof_kind": "direct-operation-structured-error",
        "surface": "function",
        "applies_when": "operation callable adapter declares structured error support",
    },
    {
        "proof_kind": "cli-process-success",
        "surface": "process",
        "applies_when": "wrapper adapter owns argv parsing or process behavior",
    },
    {
        "proof_kind": "cli-process-parser-failure",
        "surface": "process",
        "applies_when": "wrapper adapter owns argv parsing",
    },
    {
        "proof_kind": "generated-artifact-freshness",
        "surface": "freshness",
        "applies_when": "target is implemented",
    },
    {
        "proof_kind": "generated-runtime-boundary",
        "surface": "runtime-boundary",
        "applies_when": "target is implemented",
    },
    {
        "proof_kind": "unsupported-primitive-target",
        "surface": "primitive-support",
        "applies_when": "target support depends on primitive declarations",
    },
)


class TargetExtensionContractError(ValueError):
    """Raised when a target extension contract would make targets own behavior."""


@dataclass(frozen=True)
class TargetExtensionContract:
    target_id: str
    implementation_status: str
    projection_rules: Mapping[str, Any]
    runtime_dependencies: Mapping[str, Any]
    operation_callable_surface: Mapping[str, Any]
    wrapper_adapter_shape: Mapping[str, Any]
    packaging_output_layout: Mapping[str, Any]
    conformance_execution: Mapping[str, Any]
    support_declaration: Mapping[str, Any]
    product_semantics_boundary: Mapping[str, Any]
    maintenance_boundary: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "TargetExtensionContract":
        validate_target_extension_contract(raw)
        return cls(
            target_id=str(raw["target_id"]),
            implementation_status=str(raw["implementation_status"]),
            projection_rules=dict(raw["projection_rules"]),
            runtime_dependencies=dict(raw["runtime_dependencies"]),
            operation_callable_surface=dict(raw["operation_callable_surface"]),
            wrapper_adapter_shape=dict(raw["wrapper_adapter_shape"]),
            packaging_output_layout=dict(raw["packaging_output_layout"]),
            conformance_execution=dict(raw["conformance_execution"]),
            support_declaration=dict(raw["support_declaration"]),
            product_semantics_boundary=dict(raw["product_semantics_boundary"]),
            maintenance_boundary=dict(raw["maintenance_boundary"]),
        )

    @property
    def adapter_ids(self) -> tuple[str, ...]:
        values = self.support_declaration.get("adapter_ids", ())
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
            return tuple(str(value) for value in values)
        return ()

    @property
    def matrix_inclusion(self) -> str:
        return str(self.support_declaration.get("matrix_inclusion", "manual"))


def target_extension_schema_path() -> Path:
    return Path(str(resources.files("command_generation.schemas").joinpath("target_extension.schema.json")))


def _load_schema() -> dict[str, Any]:
    return json.loads(target_extension_schema_path().read_text(encoding="utf-8"))


def validate_target_extension_contract(raw: Mapping[str, Any]) -> None:
    errors = sorted(Draft202012Validator(_load_schema()).iter_errors(raw), key=lambda error: list(error.path))
    if errors:
        messages = []
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            messages.append(f"{location}: {error.message}")
        raise TargetExtensionContractError("invalid target extension contract:\n" + "\n".join(messages))

    semantics = raw.get("product_semantics_boundary", {})
    if isinstance(semantics, Mapping) and semantics.get("target_owns_product_semantics") is True:
        raise TargetExtensionContractError("target extension contract must not let a target own product operation semantics")

    maintenance = raw.get("maintenance_boundary", {})
    if isinstance(maintenance, Mapping) and maintenance.get("per_operation_feature_maintenance") is True:
        raise TargetExtensionContractError("target extension contract must not require per-operation feature maintenance")


def target_support_matrix_entries(
    contracts: Sequence[TargetExtensionContract | Mapping[str, Any]], *, operation_id: str, case_id: str
) -> tuple[dict[str, Any], ...]:
    entries: list[dict[str, Any]] = []
    for contract_or_mapping in contracts:
        contract = (
            contract_or_mapping
            if isinstance(contract_or_mapping, TargetExtensionContract)
            else TargetExtensionContract.from_mapping(contract_or_mapping)
        )
        if contract.implementation_status != "implemented":
            continue
        if contract.matrix_inclusion != "automatic-when-target-implemented":
            continue
        for adapter_id in contract.adapter_ids:
            entries.append(
                {
                    "operation_id": operation_id,
                    "case_id": case_id,
                    "target_id": contract.target_id,
                    "adapter_id": adapter_id,
                    "source": "target-extension support declaration",
                }
            )
    return tuple(entries)


def required_target_proof_matrix_entries(
    contracts: Sequence[TargetExtensionContract | Mapping[str, Any]],
) -> tuple[dict[str, str], ...]:
    """Project implemented target-extension contracts into required generic proof rows."""

    entries: list[dict[str, str]] = []
    for contract_or_mapping in contracts:
        contract = (
            contract_or_mapping
            if isinstance(contract_or_mapping, TargetExtensionContract)
            else TargetExtensionContract.from_mapping(contract_or_mapping)
        )
        if contract.implementation_status != "implemented":
            continue
        adapter_id = str(contract.operation_callable_surface.get("adapter_id", "")).strip()
        raw_wrapper_owns = contract.wrapper_adapter_shape.get("owns", ())
        wrapper_owns = (
            {str(item) for item in raw_wrapper_owns}
            if isinstance(raw_wrapper_owns, Sequence) and not isinstance(raw_wrapper_owns, (str, bytes))
            else set()
        )
        primitive_support = str(contract.support_declaration.get("primitive_support", "declared")).strip() or "declared"

        if adapter_id:
            entries.append(_proof_entry(contract, "direct-operation-success", adapter_id=adapter_id))
            if contract.operation_callable_surface.get("structured_errors") is True:
                entries.append(_proof_entry(contract, "direct-operation-structured-error", adapter_id=adapter_id))
        if "argv parsing" in wrapper_owns or "process behavior" in wrapper_owns or "exit-code mapping" in wrapper_owns:
            entries.append(_proof_entry(contract, "cli-process-success", adapter_id=adapter_id or "process"))
        if "argv parsing" in wrapper_owns:
            entries.append(_proof_entry(contract, "cli-process-parser-failure", adapter_id=adapter_id or "process"))
        entries.append(_proof_entry(contract, "generated-artifact-freshness", adapter_id=adapter_id or contract.target_id))
        entries.append(_proof_entry(contract, "generated-runtime-boundary", adapter_id=adapter_id or contract.target_id))
        if primitive_support != "not-applicable":
            entries.append(_proof_entry(contract, "unsupported-primitive-target", adapter_id=adapter_id or contract.target_id))
    return tuple(entries)


def missing_target_proof_matrix_entries(
    required_entries: Sequence[Mapping[str, str]], evidence_ids: Sequence[str] | set[str] | tuple[str, ...]
) -> tuple[dict[str, str], ...]:
    """Return required target proof rows that are not backed by explicit evidence ids."""

    evidence = {str(item) for item in evidence_ids}
    return tuple(dict(entry) for entry in required_entries if str(entry.get("evidence_id", "")) not in evidence)


def _proof_entry(contract: TargetExtensionContract, proof_kind: str, *, adapter_id: str) -> dict[str, str]:
    return {
        "target_id": contract.target_id,
        "adapter_id": adapter_id,
        "proof_kind": proof_kind,
        "evidence_id": f"{contract.target_id}:{adapter_id}:{proof_kind}",
        "source": "required target proof matrix",
    }
