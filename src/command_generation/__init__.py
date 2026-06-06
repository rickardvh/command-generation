"""Generic command package generation boundary."""

from __future__ import annotations

from command_generation.artifacts import CanonicalCommandArtifact, canonical_command_artifacts
from command_generation.conformance import (
    CliConformanceFailure,
    CliConformanceResult,
    CliConformanceTarget,
    ProcessConformanceCase,
    expected_contract_fields,
    materialize_case_fixture,
    process_case_from_contract,
    run_cli_conformance_case,
    selected_contract_fields,
)
from command_generation.generator import GeneratedOutput, generate_command_packages, generated_output_freshness_report, render_outputs
from command_generation.host_manifest import CommandGenerationHostManifest
from command_generation.ir import command_package_schema_path, load_command_package_ir
from command_generation.primitive_registry import BUILTIN_PORTABLE_PRIMITIVES, PrimitiveDefinition, PrimitiveRegistry
from command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, execute_primitive, run_operation_steps

__all__ = [
    "BUILTIN_PORTABLE_PRIMITIVES",
    "CanonicalCommandArtifact",
    "CliConformanceFailure",
    "CliConformanceResult",
    "CliConformanceTarget",
    "CommandGenerationHostManifest",
    "GeneratedOutput",
    "PrimitiveDefinition",
    "PrimitiveContext",
    "PrimitiveExecutionError",
    "ProcessConformanceCase",
    "PrimitiveRegistry",
    "canonical_command_artifacts",
    "command_package_schema_path",
    "execute_primitive",
    "expected_contract_fields",
    "generate_command_packages",
    "generated_output_freshness_report",
    "load_command_package_ir",
    "materialize_case_fixture",
    "process_case_from_contract",
    "render_outputs",
    "run_cli_conformance_case",
    "run_operation_steps",
    "selected_contract_fields",
]
