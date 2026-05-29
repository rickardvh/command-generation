from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from command_generation import (
    BUILTIN_PORTABLE_PRIMITIVES,
    CommandGenerationHostManifest,
    PrimitiveRegistry,
    command_package_schema_path,
    generate_command_packages,
    load_command_package_ir,
    render_outputs,
)


def _maturity_policy() -> dict[str, object]:
    return {
        "authority_rule": "fixture contracts own generated command surfaces.",
        "runtime_boundary": "fixture runtime executes portable IR only.",
        "ordinary_development_environment": "local pytest",
        "test_environment": "local pytest",
        "custom_codegen_boundary": "none",
        "shell_adapter_policy": "none",
        "direct_cli_edit_policy": "generated files are not edited directly",
        "extraction_readiness": {
            "status": "ready",
            "owner": "fixture",
            "rule": "no host-specific code in generic renderer",
            "accepted_couplings": [],
        },
        "python_cli_completion": {
            "current_state": "full-generated-cli-complete",
            "finish_line": "fixture command executes portable IR",
            "allowed_hand_owned_cli_responsibilities": ["package metadata lookup"],
            "must_move_behind_contracts_or_generation": ["none"],
            "proof_requirements": ["fixture conformance"],
            "completion_gate": {
                "state": "satisfied",
                "scope": "python-only",
                "satisfied_by": [{"id": "fixture-conformance", "proof": "pytest", "evidence": "non-AW fixture test"}],
            },
        },
        "generated_package_maturity": {
            "routing_rule": "weak-agent-safe fixture",
            "levels": [
                {
                    "id": "weak-agent-safe-adapter",
                    "summary": "Runnable read-only fixture package.",
                    "runtime_backed": True,
                    "promotion_requires": ["fixture conformance"],
                    "weak_agent_routing": "allowed-read-only",
                    "runnable": True,
                }
            ]
        },
        "non_python_runtime_binding": {
            "selected_model": "native runtime",
            "default_runtime_command": "node-native",
            "scope": "fixture",
            "universal_contract_owns": ["command identity"],
            "target_projection_owns": ["argv"],
            "runtime_owns": ["portable primitives"],
            "error_mapping": ["runtime errors fail"],
        },
    }


def _fixture_manifest(tmp_path: Path) -> dict[str, object]:
    (tmp_path / "contracts" / "operations").mkdir(parents=True)
    (tmp_path / "payload").mkdir()
    (tmp_path / "payload" / "todos.json").write_text(
        json.dumps([{"title": "Write test"}, {"title": "Run test"}]),
        encoding="utf-8",
    )
    operation = {
        "schema_version": "agentic-workspace/operation/v1",
        "id": "todo.list.report",
        "migration_status": "runtime-consumed",
        "ir_plan": {
            "status": "complete",
            "steps": [
                {
                    "id": "read_todos",
                    "uses": "filesystem.read",
                    "arguments": {"root": "todo.package-payload", "path": "todos.json"},
                    "outputs": ["todo_text"],
                },
                {"id": "parse_todos", "uses": "json.parse", "arguments": {"source": "todo_text"}, "outputs": ["todos"]},
                {
                    "id": "assemble",
                    "uses": "payload.assemble",
                    "arguments": {
                        "fields": {
                            "template": {
                                "kind": "todo-list/v1",
                                "item_count": {"$count": "todos"},
                                "items": {"$value": "todos"},
                            }
                        }
                    },
                    "outputs": ["result"],
                },
                {"id": "emit", "uses": "output.emit", "outputs": ["emitted"]},
            ],
        },
    }
    (tmp_path / "contracts" / "operations" / "todo.list.report.json").write_text(
        json.dumps(operation, indent=2),
        encoding="utf-8",
    )
    return {
        "schema_version": "agentic-workspace/command-package-ir/v1",
        "summary": "Non-AW fixture command package.",
        "schema": "schemas/command_package_ir.schema.json",
        "source_contracts": ["contracts/operations/todo.list.report.json"],
        "generation_policy": _maturity_policy(),
        "packages": [
            {
                "id": "todo-fixture",
                "program": "todoctl",
                "package_role": "root-workspace-cli",
                "operation_contract_root": "contracts",
                "version_metadata": {
                    "source": "python-package-metadata",
                    "distribution": "todo-fixture",
                    "fallback_version": "0.0.0",
                },
                "targets": [
                    {
                        "kind": "python",
                        "package_name": "todo-fixture",
                        "generated_root": "todo_cli_pkg",
                        "entrypoints": ["todoctl"],
                        "test_environment": "python-dev",
                        "maturity_level_ref": "weak-agent-safe-adapter",
                    }
                ],
                "commands": [
                    {
                        "adapter_id": "todo.list.cli",
                        "status": "generated",
                        "command": {"name": "list"},
                        "interface": {
                            "name": "list",
                            "help": "List todos.",
                            "options": [
                                {
                                    "name": "format",
                                    "flags": ["--format"],
                                    "choices": ["text", "json"],
                                    "default": "json",
                                    "help": "Output format.",
                                }
                            ],
                        },
                        "operation_ref": {"id": "todo.list.report", "path": "operations/todo.list.report.json"},
                        "runtime_binding": {
                            "kind": "operation-primitive-sequence",
                            "primitive_refs": ["filesystem.read", "json.parse", "payload.assemble", "output.emit"],
                        },
                        "schemas": {"input": [], "output": []},
                        "effect_hints": {
                            "read_only": True,
                            "destructive": False,
                            "idempotent": True,
                            "writes_repo_state": False,
                            "requires_preflight_gate": False,
                        },
                        "conformance_refs": ["todo.list.process"],
                        "projection_boundary": {
                            "universal": ["command identity"],
                            "target_specific": ["parser wiring"],
                            "runtime_owned": ["portable primitive execution"],
                        },
                    }
                ],
                "python_runtime_binding": {
                    "entrypoint": "todoctl",
                    "default_runtime_command": "python -m todo_cli_pkg.cli",
                    "runtime_module_file": "cli",
                    "render_runtime_module": True,
                    "resource_copies": [
                        {"source_root": "payload", "generated_root": "_payload", "required_marker": "todos.json"}
                    ],
                    "operation_executor": {
                        "module_file": "primitives.operation_executor",
                        "supported_operation_ids": ["todo.list.report"],
                        "initial_values": [{"name": "format", "arg": "format", "default": "json"}],
                        "context_roots": [
                            {"name": "todo.package-payload", "generated_root": "_payload", "required_marker": "todos.json"}
                        ],
                        "handlers": [
                            {
                                "primitive": "todo.unused",
                                "handler": "generated_target_root_resolve",
                                "project_markers": ["pyproject.toml"],
                            }
                        ],
                    },
                    "runtime_module_handlers": [],
                    "local_runtime_bindings": [],
                },
            }
        ],
    }


def test_package_owned_schema_loads_fixture_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "command_package_ir.json"
    manifest_path.write_text(json.dumps(_fixture_manifest(tmp_path)), encoding="utf-8")

    loaded = load_command_package_ir(manifest_path, command_package_schema_path())

    assert loaded["packages"][0]["id"] == "todo-fixture"


def test_non_aw_fixture_renders_and_runs_python_command(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)

    stale = generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    assert stale == []
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); from todo_cli_pkg.cli import main; raise SystemExit(main(['list', '--format', 'json']))",
            str(tmp_path),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["item_count"] == 2
    assert "agentic_workspace" not in (tmp_path / "todo_cli_pkg" / "cli.py").read_text(encoding="utf-8")


def test_generic_generator_source_has_no_aw_product_literals() -> None:
    source = (Path(__file__).resolve().parents[1] / "src" / "command_generation" / "generator.py").read_text(encoding="utf-8")

    forbidden = [
        "agentic-workspace",
        "agentic-planning",
        "agentic-memory",
        "agentic-verification",
        ".agentic-workspace",
        "workspace.",
        "planning.",
        "memory.",
        "verification.",
    ]
    assert [token for token in forbidden if token in source] == []


def test_primitive_registry_rejects_unsupported_target(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)
    registry = PrimitiveRegistry.from_definitions(
        [
            {
                "id": "filesystem.read",
                "kind": "portable",
                "target_support": {"python": "unsupported"},
                "unsupported_targets": {"python": "fixture intentionally disables file reads"},
            }
        ]
    )

    with pytest.raises(ValueError, match="unsupported command-generation primitive"):
        render_outputs(
            manifest,
            repo_root=tmp_path,
            source_path="command_package_ir.json",
            regenerate_command="python generate.py",
            host_manifest=CommandGenerationHostManifest(primitive_registry=registry),
        )


def test_primitive_registry_round_trips_host_metadata() -> None:
    registry = PrimitiveRegistry.from_definitions(
        [
            {
                "id": "todo.domain.load",
                "kind": "host",
                "description": "Load fixture domain payload.",
                "input_schema_ref": "contracts/operations/todo.list.report.json#/inputs",
                "output_schema_ref": "contracts/operations/todo.list.report.json#/output",
                "effects": {"read_only": True, "writes_repo_state": False},
                "target_support": {"python": "host-implemented", "typescript": "unsupported"},
                "owner": "fixture",
                "conformance_ref": "todo.list.process",
                "unsupported_targets": {"typescript": "fixture has no TypeScript domain runtime"},
            }
        ]
    )

    definition = registry.ensure_supported("todo.domain.load", "python")

    assert definition.input_schema_ref.endswith("#/inputs")
    assert definition.output_schema_ref.endswith("#/output")
    assert definition.effects["read_only"] is True
    assert definition.conformance_refs == ("todo.list.process",)
    with pytest.raises(ValueError, match="fixture has no TypeScript domain runtime"):
        registry.ensure_supported("todo.domain.load", "typescript")
    assert registry.to_jsonable()[0]["unsupported_targets"]["typescript"] == "fixture has no TypeScript domain runtime"


def test_builtin_registry_declares_portable_primitives() -> None:
    assert "filesystem.read" in BUILTIN_PORTABLE_PRIMITIVES.ids()
    assert "output.emit" in BUILTIN_PORTABLE_PRIMITIVES.ids()
