"""Generic command package generation boundary."""

from __future__ import annotations

from command_generation.artifacts import CanonicalCommandArtifact, canonical_command_artifacts
from command_generation.generator import GeneratedOutput, generate_command_packages, render_outputs
from command_generation.host_manifest import CommandGenerationHostManifest
from command_generation.ir import command_package_schema_path, load_command_package_ir
from command_generation.primitive_registry import BUILTIN_PORTABLE_PRIMITIVES, PrimitiveDefinition, PrimitiveRegistry
from command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, execute_primitive, run_operation_steps

__all__ = [
    "BUILTIN_PORTABLE_PRIMITIVES",
    "CanonicalCommandArtifact",
    "CommandGenerationHostManifest",
    "GeneratedOutput",
    "PrimitiveDefinition",
    "PrimitiveContext",
    "PrimitiveExecutionError",
    "PrimitiveRegistry",
    "canonical_command_artifacts",
    "command_package_schema_path",
    "execute_primitive",
    "generate_command_packages",
    "load_command_package_ir",
    "render_outputs",
    "run_operation_steps",
]
