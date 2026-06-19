from __future__ import annotations

import json
import importlib
import shutil
import subprocess
import sys
import types
from collections.abc import Callable, Mapping
from importlib.metadata import version as package_version
from pathlib import Path
from typing import cast

import pytest

import command_generation as command_generation_api
from command_generation import (
    BUILTIN_PORTABLE_PRIMITIVES,
    canonical_command_artifacts,
    CliConformanceTarget,
    CommandGenerationHostManifest,
    FunctionConformanceTarget,
    GeneratedOutput,
    PrimitiveContext,
    PrimitiveRegistry,
    TypescriptFunctionConformanceTarget,
    command_package_schema_path,
    contract_conformance_cases_manifest,
    conformance_ownership_inventory,
    execute_primitive,
    generate_command_packages,
    generated_output_freshness_report,
    load_command_package_ir,
    load_contract_conformance_case,
    materialize_case_fixture,
    missing_target_proof_matrix_entries,
    operation_case_from_contract,
    process_case_from_contract,
    required_target_proof_matrix_entries,
    render_outputs,
    run_function_conformance_case,
    run_typescript_function_conformance_case,
    run_cli_conformance_case,
    target_extension_schema_path,
    target_support_matrix_entries,
    validate_target_extension_contract,
)
from command_generation.target_extension import (
    TargetExtensionContract,
    TargetExtensionContractError,
    current_target_proof_evidence_inventory,
    structured_target_proof_evidence_inventory,
)
from command_generation.targets.contract import PYTHON_TARGET_LAYOUT_VERSION, TYPESCRIPT_TARGET_LAYOUT_VERSION
from command_generation.targets.python import _python_local_runtime_binding_module


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
        "schema_version": "command-generation/operation/v1",
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
                                "requested_format": {"$value": "output_format"},
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
        "schema_version": "command-generation/command-package-ir/v1",
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
                        "initial_values": [
                            {"name": "format", "arg": "format", "default": "json"},
                            {"name": "output_format", "arg": "format", "default": "json"},
                        ],
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


def _fixture_manifest_with_typescript(tmp_path: Path) -> dict[str, object]:
    manifest = _fixture_manifest(tmp_path)
    package = cast(dict[str, object], cast(list[object], manifest["packages"])[0])
    targets = cast(list[object], package["targets"])
    targets.append(
        {
            "kind": "typescript",
            "package_name": "todo-fixture-typescript",
            "generated_root": "todo_ts_pkg",
            "entrypoints": ["todoctl-ts"],
            "test_environment": "node-dev",
            "maturity_level_ref": "weak-agent-safe-adapter",
            "generation_status": "generated",
        }
    )
    return manifest


def _fixture_manifest_with_typescript_append_option(tmp_path: Path) -> dict[str, object]:
    manifest = _fixture_manifest_with_typescript(tmp_path)
    package = cast(dict[str, object], cast(list[object], manifest["packages"])[0])
    command = cast(dict[str, object], cast(list[object], package["commands"])[0])
    interface = cast(dict[str, object], command["interface"])
    options = cast(list[object], interface["options"])
    options.append(
        {
            "name": "tags",
            "flags": ["--tag"],
            "action": "append",
            "help": "Tag filter.",
        }
    )
    operation_path = tmp_path / "contracts" / "operations" / "todo.list.report.json"
    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    steps = cast(list[object], cast(dict[str, object], operation["ir_plan"])["steps"])
    assemble = cast(dict[str, object], steps[2])
    template = cast(dict[str, object], cast(dict[str, object], cast(dict[str, object], assemble["arguments"])["fields"])["template"])
    template["tags"] = {"$value": "tags"}
    operation_path.write_text(json.dumps(operation, indent=2), encoding="utf-8")
    return manifest


def _fixture_manifest_with_nested_cli_shapes(tmp_path: Path) -> dict[str, object]:
    manifest = _fixture_manifest_with_typescript(tmp_path)
    package = cast(dict[str, object], cast(list[object], manifest["packages"])[0])
    command = cast(dict[str, object], cast(list[object], package["commands"])[0])
    operation_ref = {"id": "todo.list.report", "path": "operations/todo.list.report.json"}
    command["interface"] = {
        "name": "list",
        "help": "List todos.",
        "subcommand_dest": "todo_scope",
        "subcommands_required": True,
        "subcommands": [
            {
                "name": "project",
                "help": "List todos for a project.",
                "arguments": [{"name": "project", "help": "Project name."}],
                "options": [
                    {
                        "name": "format",
                        "flags": ["--format"],
                        "choices": ["text", "json"],
                        "default": "json",
                        "help": "Output format.",
                    },
                    {
                        "name": "priority",
                        "flags": ["--priority"],
                        "choices": ["low", "high"],
                        "required": True,
                        "help": "Priority filter.",
                    },
                    {
                        "name": "tags",
                        "flags": ["--tag"],
                        "action": "append",
                        "help": "Tag filter.",
                    },
                ],
                "operation_ref": operation_ref,
            }
        ],
    }
    operation_executor = cast(dict[str, object], cast(dict[str, object], package["python_runtime_binding"])["operation_executor"])
    operation_executor["initial_values"] = [
        {"name": "format", "arg": "format", "default": "json"},
        {"name": "output_format", "arg": "format", "default": "json"},
        {"name": "project", "arg": "project", "default": ""},
        {"name": "priority", "arg": "priority", "default": ""},
        {"name": "tags", "arg": "tags", "default": []},
    ]
    operation_path = tmp_path / "contracts" / "operations" / "todo.list.report.json"
    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    assemble = cast(dict[str, object], cast(list[object], cast(dict[str, object], operation["ir_plan"])["steps"])[2])
    template = cast(dict[str, object], cast(dict[str, object], cast(dict[str, object], assemble["arguments"])["fields"])["template"])
    template["project"] = {"$value": "project"}
    template["priority"] = {"$value": "priority"}
    template["tags"] = {"$value": "tags"}
    operation_path.write_text(json.dumps(operation, indent=2), encoding="utf-8")
    return manifest


def _fixture_manifest_with_host_owned_python_primitive(tmp_path: Path) -> dict[str, object]:
    manifest = _fixture_manifest(tmp_path)
    (tmp_path / "todo_host_primitive_support.py").write_text(
        "def execute_host_primitive(primitive, *, values, arguments, context):\n"
        "    if primitive != 'todo.decorate':\n"
        "        raise RuntimeError(f'unsupported fixture primitive: {primitive}')\n"
        "    enriched = dict(values['result'])\n"
        "    enriched['host_marker'] = 'decorated-by-python-host'\n"
        "    return enriched\n",
        encoding="utf-8",
    )
    package = cast(dict[str, object], cast(list[object], manifest["packages"])[0])
    command = cast(dict[str, object], cast(list[object], package["commands"])[0])
    runtime_binding = cast(dict[str, object], command["runtime_binding"])
    runtime_binding["primitive_refs"] = [*cast(list[str], runtime_binding["primitive_refs"]), "todo.decorate"]
    operation_path = tmp_path / "contracts" / "operations" / "todo.list.report.json"
    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    steps = cast(list[object], cast(dict[str, object], operation["ir_plan"])["steps"])
    steps.insert(
        3,
        {
            "id": "decorate_result",
            "uses": "todo.decorate",
            "arguments": {},
            "outputs": ["result"],
        },
    )
    operation_path.write_text(json.dumps(operation, indent=2), encoding="utf-8")
    return manifest


def _fixture_manifest_with_host_owned_typescript_primitive(tmp_path: Path) -> dict[str, object]:
    manifest = _fixture_manifest_with_typescript(tmp_path)
    (tmp_path / "todoHostPrimitiveSupport.mjs").write_text(
        "export function executeHostPrimitive(primitive, values) {\n"
        "  if (primitive !== 'todo.decorate') throw new Error(`unsupported fixture primitive ${primitive}`);\n"
        "  return { ...values.result, host_marker: 'decorated-by-ts-host' };\n"
        "}\n",
        encoding="utf-8",
    )
    package = cast(dict[str, object], cast(list[object], manifest["packages"])[0])
    targets = cast(list[object], package["targets"])
    package["targets"] = [target for target in targets if cast(dict[str, object], target)["kind"] == "typescript"]
    command = cast(dict[str, object], cast(list[object], package["commands"])[0])
    runtime_binding = cast(dict[str, object], command["runtime_binding"])
    runtime_binding["primitive_refs"] = [*cast(list[str], runtime_binding["primitive_refs"]), "todo.decorate"]
    operation_path = tmp_path / "contracts" / "operations" / "todo.list.report.json"
    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    steps = cast(list[object], cast(dict[str, object], operation["ir_plan"])["steps"])
    steps.insert(
        3,
        {
            "id": "decorate_result",
            "uses": "todo.decorate",
            "arguments": {},
            "outputs": ["result"],
        },
    )
    operation_path.write_text(json.dumps(operation, indent=2), encoding="utf-8")
    return manifest


def test_package_owned_schema_loads_fixture_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "command_package_ir.json"
    manifest_path.write_text(json.dumps(_fixture_manifest(tmp_path)), encoding="utf-8")

    loaded = load_command_package_ir(manifest_path, command_package_schema_path())

    schema = json.loads(command_package_schema_path().read_text(encoding="utf-8"))
    assert schema["$id"] == "command-generation/command-package-ir.schema.json"
    assert schema["title"] == "Command Generation Command Package IR"
    assert schema["properties"]["schema_version"]["const"] == "command-generation/command-package-ir/v1"
    assert schema["x-command-generation-doc-role"] == "contract-reference"
    assert "x-agentic-workspace-doc-role" not in schema
    assert loaded["schema_version"] == "command-generation/command-package-ir/v1"
    assert loaded["packages"][0]["id"] == "todo-fixture"


def test_package_owned_schema_accepts_legacy_aw_schema_version_alias(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)
    manifest["schema_version"] = "agentic-workspace/command-package-ir/v1"
    manifest_path = tmp_path / "command_package_ir.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    loaded = load_command_package_ir(manifest_path, command_package_schema_path())

    assert loaded["schema_version"] == "command-generation/command-package-ir/v1"
    assert loaded["packages"][0]["id"] == "todo-fixture"


def test_loaded_legacy_schema_alias_renders_canonical_generation_metadata(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)
    manifest["schema_version"] = "agentic-workspace/command-package-ir/v1"
    manifest_path = tmp_path / "command_package_ir.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    loaded = load_command_package_ir(manifest_path, command_package_schema_path())
    outputs = render_outputs(
        loaded,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
    )
    rendered = {output.path.relative_to(tmp_path).as_posix(): output.content for output in outputs}

    assert json.loads(rendered["todo_cli_pkg/command_package.json"])["generation_metadata"]["source_ir"] == {
        "schema_version": "command-generation/command-package-ir/v1"
    }


def test_target_extension_schema_copies_match() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_schema = repo_root / "schemas" / "target_extension.schema.json"

    assert source_schema.read_bytes() == target_extension_schema_path().read_bytes()


def test_public_api_exports_have_compatibility_classification() -> None:
    classification = command_generation_api.PUBLIC_API_CLASSIFICATION
    docs = (Path(__file__).resolve().parents[1] / "docs" / "public-api.md").read_text(encoding="utf-8")

    assert set(classification) == set(command_generation_api.__all__)
    assert set(classification.values()) <= {"stable", "provisional"}
    for symbol, status in classification.items():
        assert f"| `{symbol}` | {status} |" in docs

    assert classification["load_command_package_ir"] == "stable"
    assert classification["render_outputs"] == "stable"
    assert classification["generate_command_packages"] == "stable"
    assert classification["run_cli_conformance_case"] == "stable"
    assert classification["invoke_typescript_operation"] == "provisional"
    assert classification["execute_primitive"] == "provisional"


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
    payload = json.loads(result.stdout)
    assert payload["item_count"] == 2
    assert payload["requested_format"] == "json"
    assert "agentic_workspace" not in (tmp_path / "todo_cli_pkg" / "cli.py").read_text(encoding="utf-8")
    package_resource = json.loads((tmp_path / "todo_cli_pkg" / "command_package.json").read_text(encoding="utf-8"))
    metadata = package_resource["generation_metadata"]
    assert metadata["schema_version"] == "command-generation/generated-artifact-metadata/v1"
    assert metadata["generator"] == {"package": "command-generation", "version": package_version("command-generation")}
    assert metadata["source_ir"]["schema_version"] == "command-generation/command-package-ir/v1"
    assert metadata["target"] == {
        "kind": "python",
        "package_name": "todo-fixture",
        "layout_version": "command-generation/python-target-layout/v1",
    }


def test_non_aw_fixture_python_cli_reports_parser_failure(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)

    generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); from todo_cli_pkg.cli import main; raise SystemExit(main(['list', '--format', 'yaml']))",
            str(tmp_path),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_non_aw_fixture_renders_python_operation_callable(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)

    stale = generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    assert stale == []
    sys.path.insert(0, str(tmp_path))
    try:
        invoke = importlib.import_module("todo_cli_pkg.commands.todo_list_report").invoke

        result = invoke({"format": "json", "output_format": "text"})
    finally:
        sys.path.remove(str(tmp_path))
        for module_name in list(sys.modules):
            if module_name == "todo_cli_pkg" or module_name.startswith("todo_cli_pkg."):
                sys.modules.pop(module_name, None)
    assert result == {
        "kind": "todo-list/v1",
        "item_count": 2,
        "items": [{"title": "Write test"}, {"title": "Run test"}],
        "requested_format": "text",
    }


def test_non_aw_fixture_python_cli_covers_nested_required_positional_and_append(tmp_path: Path) -> None:
    manifest = _fixture_manifest_with_nested_cli_shapes(tmp_path)

    stale = generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.path.insert(0, sys.argv[1]); "
                "from todo_cli_pkg.cli import main; "
                "raise SystemExit(main(['list', 'project', 'alpha', '--priority', 'high', '--tag', 'docs', '--tag', 'tests', '--format', 'json']))"
            ),
            str(tmp_path),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert stale == []
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["project"] == "alpha"
    assert payload["priority"] == "high"
    assert payload["tags"] == ["docs", "tests"]


def test_non_aw_fixture_python_cli_validates_required_nested_option(tmp_path: Path) -> None:
    generate_command_packages(
        _fixture_manifest_with_nested_cli_shapes(tmp_path),
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.path.insert(0, sys.argv[1]); "
                "from todo_cli_pkg.cli import main; "
                "raise SystemExit(main(['list', 'project', 'alpha']))"
            ),
            str(tmp_path),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--priority" in result.stderr


def test_non_aw_fixture_python_host_owned_primitive_success_path(tmp_path: Path) -> None:
    registry = PrimitiveRegistry.from_definitions(
        [
            {
                "id": "todo.decorate",
                "kind": "host-owned",
                "description": "Fixture host-owned result decorator.",
                "target_support": {"python": "host-implemented"},
                "owner": "todo fixture",
            }
        ]
    )

    stale = generate_command_packages(
        _fixture_manifest_with_host_owned_python_primitive(tmp_path),
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
        host_manifest=CommandGenerationHostManifest(
            primitive_registry=registry,
            python_primitive_support_path=tmp_path / "todo_host_primitive_support.py",
        ),
    )
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

    assert stale == []
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["host_marker"] == "decorated-by-python-host"


def test_non_aw_fixture_python_host_owned_primitive_requires_support_module(tmp_path: Path) -> None:
    registry = PrimitiveRegistry.from_definitions(
        [
            {
                "id": "todo.decorate",
                "kind": "host-owned",
                "description": "Fixture host-owned result decorator.",
                "target_support": {"python": "host-implemented"},
                "owner": "todo fixture",
            }
        ]
    )

    generate_command_packages(
        _fixture_manifest_with_host_owned_python_primitive(tmp_path),
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
        host_manifest=CommandGenerationHostManifest(primitive_registry=registry),
    )
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

    assert result.returncode == 1
    assert "unsupported host primitive: 'todo.decorate'" in result.stderr


def test_non_aw_fixture_accepts_host_primitive_registry_extension(tmp_path: Path) -> None:
    manifest = _fixture_manifest_with_typescript(tmp_path)
    package = cast(dict[str, object], cast(list[object], manifest["packages"])[0])
    command = cast(dict[str, object], cast(list[object], package["commands"])[0])
    runtime_binding = cast(dict[str, object], command["runtime_binding"])
    runtime_binding["primitive_refs"] = [*cast(list[str], runtime_binding["primitive_refs"]), "todo.audit"]
    operation_path = tmp_path / "contracts" / "operations" / "todo.list.report.json"
    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    steps = cast(list[object], cast(dict[str, object], operation["ir_plan"])["steps"])
    steps.append(
        {
            "id": "audit",
            "uses": "todo.audit",
            "arguments": {"message": "fixture rendered"},
            "outputs": [],
        }
    )
    operation_path.write_text(json.dumps(operation, indent=2), encoding="utf-8")
    registry = PrimitiveRegistry.from_definitions(
        [
            {
                "id": "todo.audit",
                "kind": "host-owned",
                "description": "Fixture host-owned audit primitive.",
                "target_support": {"python": "host-implemented", "typescript": "host-implemented"},
                "owner": "todo fixture",
            }
        ]
    )

    outputs = render_outputs(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        host_manifest=CommandGenerationHostManifest(primitive_registry=registry),
    )
    rendered = {output.path.relative_to(tmp_path).as_posix(): output.content for output in outputs}

    assert "todo.audit" in rendered["todo_cli_pkg/operations/todo.list.report.json"]
    assert "todo.audit" in rendered["todo_ts_pkg/resources/operations/todo.list.report.json"]


def test_resource_copies_skip_python_cache_artifacts(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)
    cache_dir = tmp_path / "payload" / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "todos.cpython-313.pyc").write_bytes(b"\xb1\x00invalid bytecode")
    (tmp_path / "payload" / "stale.pyo").write_bytes(b"\xb1\x00invalid optimized bytecode")

    stale = generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    assert stale == []
    assert (tmp_path / "todo_cli_pkg" / "_payload" / "todos.json").is_file()
    assert not (tmp_path / "todo_cli_pkg" / "_payload" / "__pycache__").exists()
    assert not (tmp_path / "todo_cli_pkg" / "_payload" / "stale.pyo").exists()


def test_canonical_command_artifacts_expose_implementation_independent_truth(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)

    artifacts = canonical_command_artifacts(manifest)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.package_id == "todo-fixture"
    assert artifact.program == "todoctl"
    assert artifact.adapter_id == "todo.list.cli"
    assert artifact.command_name == "list"
    assert artifact.operation_ref == {"id": "todo.list.report", "path": "operations/todo.list.report.json"}
    assert artifact.runtime_binding["primitive_refs"] == ["filesystem.read", "json.parse", "payload.assemble", "output.emit"]
    assert artifact.conformance_refs == ("todo.list.process",)
    assert artifact.projection_boundary["universal"] == ("command identity",)
    assert artifact.projection_boundary["target_specific"] == ("parser wiring",)
    assert artifact.projection_boundary["runtime_owned"] == ("portable primitive execution",)


def test_canonical_command_artifacts_exclude_target_specific_package_fields(tmp_path: Path) -> None:
    artifact = canonical_command_artifacts(_fixture_manifest(tmp_path))[0]

    artifact_fields = set(artifact.__dataclass_fields__)
    assert "generated_root" not in artifact_fields
    assert "package_name" not in artifact_fields
    assert "entrypoints" not in artifact_fields
    assert "test_environment" not in artifact_fields
    assert "kind" not in artifact_fields
    rendered = repr(artifact)
    assert "spawnSync" not in rendered
    assert "argparse" not in rendered
    assert "Dockerfile" not in rendered


def test_typescript_command_package_resource_is_target_scoped(tmp_path: Path) -> None:
    outputs = render_outputs(
        _fixture_manifest_with_typescript(tmp_path),
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
    )
    rendered = {output.path.relative_to(tmp_path).as_posix(): output.content for output in outputs}
    package_resource = json.loads(rendered["todo_ts_pkg/resources/command_package.json"])
    package_json = json.loads(rendered["todo_ts_pkg/package.json"])

    assert package_resource["target_resource_scope"] == {
        "kind": "command-generation/target-scoped-package-resource/v1",
        "target_kind": "typescript",
        "target_package_name": "todo-fixture-typescript",
        "rule": "Target resources carry universal command/operation metadata plus only this target's runtime binding.",
    }
    assert [target["kind"] for target in package_resource["targets"]] == ["typescript"]
    assert package_resource["targets"][0]["package_name"] == "todo-fixture-typescript"
    assert "python_runtime_binding" not in package_resource
    assert package_resource["commands"][0]["runtime_binding"]["primitive_refs"] == [
        "filesystem.read",
        "json.parse",
        "payload.assemble",
        "output.emit",
    ]
    metadata = package_resource["generation_metadata"]
    assert metadata == package_json["agenticWorkspace"]["generationMetadata"]
    assert metadata["generator"]["version"] == package_version("command-generation")
    assert metadata["source_ir"]["schema_version"] == "command-generation/command-package-ir/v1"
    assert metadata["target"] == {
        "kind": "typescript",
        "package_name": "todo-fixture-typescript",
        "layout_version": "command-generation/typescript-target-layout/v1",
    }


def test_generated_target_layout_versions_are_declared_and_placed_in_metadata(tmp_path: Path) -> None:
    outputs = render_outputs(
        _fixture_manifest_with_typescript(tmp_path),
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
    )
    rendered = {output.path.relative_to(tmp_path).as_posix(): output.content for output in outputs}
    python_resource = json.loads(rendered["todo_cli_pkg/command_package.json"])
    typescript_resource = json.loads(rendered["todo_ts_pkg/resources/command_package.json"])
    typescript_package = json.loads(rendered["todo_ts_pkg/package.json"])

    assert PYTHON_TARGET_LAYOUT_VERSION == "command-generation/python-target-layout/v1"
    assert TYPESCRIPT_TARGET_LAYOUT_VERSION == "command-generation/typescript-target-layout/v1"
    assert python_resource["generation_metadata"]["target"]["layout_version"] == PYTHON_TARGET_LAYOUT_VERSION
    assert typescript_resource["generation_metadata"]["target"]["layout_version"] == TYPESCRIPT_TARGET_LAYOUT_VERSION
    assert typescript_package["agenticWorkspace"]["generationMetadata"] == typescript_resource["generation_metadata"]


def test_non_aw_fixture_freshness_reports_python_and_typescript_targets(tmp_path: Path) -> None:
    manifest = _fixture_manifest_with_typescript(tmp_path)

    generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )
    outputs = render_outputs(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
    )

    def family(path: Path) -> str | None:
        relative = path.relative_to(tmp_path).as_posix()
        if relative.startswith("todo_cli_pkg/"):
            return "python"
        if relative.startswith("todo_ts_pkg/"):
            return "typescript"
        return None

    fresh = generated_output_freshness_report(
        outputs,
        repo_root=tmp_path,
        required_target_families=("python", "typescript"),
        target_family_for_path=family,
    )
    (tmp_path / "todo_ts_pkg" / "src" / "cli.mjs").write_text("// stale\n", encoding="utf-8")
    stale = generated_output_freshness_report(
        outputs,
        repo_root=tmp_path,
        required_target_families=("python", "typescript"),
        target_family_for_path=family,
    )

    assert fresh["status"] == "fresh"
    assert set(fresh["rendered_output_count_by_family"]) == {"python", "typescript"}
    assert fresh["missing_target_families"] == []
    assert stale["status"] == "stale-or-incomplete"
    assert stale["stale_outputs_by_family"] == {"typescript": ["todo_ts_pkg/src/cli.mjs"]}


def test_typescript_cli_append_option_accumulates_repeated_values(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for TypeScript CLI execution")
    manifest = _fixture_manifest_with_typescript_append_option(tmp_path)

    stale = generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    result = subprocess.run(
        [
            "node",
            str(tmp_path / "todo_ts_pkg" / "src" / "cli.mjs"),
            "list",
            "--tag",
            "alpha",
            "--tag",
            "beta",
            "--format",
            "json",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert stale == []
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["tags"] == ["alpha", "beta"]


def test_typescript_cli_append_option_defaults_to_empty_list(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for TypeScript CLI execution")
    manifest = _fixture_manifest_with_typescript_append_option(tmp_path)

    generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    result = subprocess.run(
        ["node", str(tmp_path / "todo_ts_pkg" / "src" / "cli.mjs"), "list", "--format", "json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["tags"] == []


def test_typescript_cli_append_option_requires_value(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for TypeScript CLI execution")
    manifest = _fixture_manifest_with_typescript_append_option(tmp_path)

    generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    result = subprocess.run(
        ["node", str(tmp_path / "todo_ts_pkg" / "src" / "cli.mjs"), "list", "--tag"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "--tag requires a value" in result.stderr


def test_typescript_cli_append_option_validates_choices(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for TypeScript CLI execution")
    manifest = _fixture_manifest_with_typescript_append_option(tmp_path)
    package = cast(dict[str, object], cast(list[object], manifest["packages"])[0])
    command = cast(dict[str, object], cast(list[object], package["commands"])[0])
    interface = cast(dict[str, object], command["interface"])
    tag_option = cast(dict[str, object], cast(list[object], interface["options"])[1])
    tag_option["choices"] = ["alpha", "beta"]

    generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )

    result = subprocess.run(
        ["node", str(tmp_path / "todo_ts_pkg" / "src" / "cli.mjs"), "list", "--tag", "alpha", "--tag", "gamma"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "--tag must be one of: alpha, beta" in result.stderr


def test_non_aw_fixture_typescript_host_owned_primitive_success_path(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for TypeScript host-owned primitive execution")
    registry = PrimitiveRegistry.from_definitions(
        [
            {
                "id": "todo.decorate",
                "kind": "host-owned",
                "description": "Fixture host-owned TypeScript result decorator.",
                "target_support": {"typescript": "host-implemented"},
                "owner": "todo fixture",
            }
        ]
    )

    stale = generate_command_packages(
        _fixture_manifest_with_host_owned_typescript_primitive(tmp_path),
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
        host_manifest=CommandGenerationHostManifest(
            primitive_registry=registry,
            typescript_primitive_support_path=tmp_path / "todoHostPrimitiveSupport.mjs",
        ),
    )
    runner = tmp_path / "run-ts-host-primitive.mjs"
    runner.write_text(
        "const runtime = await import('./todo_ts_pkg/src/runtime.mjs');\n"
        "const result = runtime.invokeGeneratedOperation({\n"
        "  operationId: 'todo.list.report',\n"
        "  operationPath: 'operations/todo.list.report.json',\n"
        "  values: { format: 'json', output_format: 'json' },\n"
        "});\n"
        "console.log(JSON.stringify(result));\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["node", str(runner)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert stale == []
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["host_marker"] == "decorated-by-ts-host"


def test_non_aw_fixture_typescript_host_owned_primitive_requires_target_support(tmp_path: Path) -> None:
    registry = PrimitiveRegistry.from_definitions(
        [
            {
                "id": "todo.decorate",
                "kind": "host-owned",
                "description": "Fixture host-owned TypeScript result decorator.",
                "target_support": {"typescript": "unsupported"},
                "unsupported_targets": {"typescript": "fixture host primitive is intentionally missing"},
                "owner": "todo fixture",
            }
        ]
    )

    with pytest.raises(ValueError, match="fixture host primitive is intentionally missing"):
        render_outputs(
            _fixture_manifest_with_host_owned_typescript_primitive(tmp_path),
            repo_root=tmp_path,
            source_path="command_package_ir.json",
            regenerate_command="python generate.py",
            host_manifest=CommandGenerationHostManifest(primitive_registry=registry),
        )


def test_non_aw_fixture_typescript_cli_covers_nested_required_positional_and_append(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for TypeScript CLI execution")

    stale = generate_command_packages(
        _fixture_manifest_with_nested_cli_shapes(tmp_path),
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )
    result = subprocess.run(
        [
            "node",
            str(tmp_path / "todo_ts_pkg" / "src" / "cli.mjs"),
            "list",
            "project",
            "alpha",
            "--priority",
            "high",
            "--tag",
            "docs",
            "--tag",
            "tests",
            "--format",
            "json",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert stale == []
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["project"] == "alpha"
    assert payload["priority"] == "high"
    assert payload["tags"] == ["docs", "tests"]


def test_non_aw_fixture_typescript_cli_validates_required_nested_option(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for TypeScript CLI execution")

    generate_command_packages(
        _fixture_manifest_with_nested_cli_shapes(tmp_path),
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )
    result = subprocess.run(
        ["node", str(tmp_path / "todo_ts_pkg" / "src" / "cli.mjs"), "list", "project", "alpha"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "missing required option --priority" in result.stderr


def test_generated_targets_include_operation_fragment_support(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)
    operation_path = tmp_path / "contracts" / "operations" / "todo.list.report.json"
    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    read_step = operation["ir_plan"]["steps"].pop(0)
    operation["ir_plan"]["fragments"] = [{"id": "load-todos", "steps": [read_step]}]
    operation["ir_plan"]["steps"].insert(0, {"id": "load", "uses_fragment": "load-todos"})
    operation_path.write_text(json.dumps(operation, indent=2), encoding="utf-8")

    outputs = render_outputs(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
    )
    rendered = {output.path.relative_to(tmp_path).as_posix(): output.content for output in outputs}

    assert json.loads(rendered["todo_cli_pkg/operations/todo.list.report.json"])["ir_plan"]["fragments"][0]["id"] == "load-todos"
    assert "expand_operation_steps" in rendered["todo_cli_pkg/primitives/primitive_executor.py"]
    assert "def expand_operation_steps" in rendered["todo_cli_pkg/primitives/operation_composition.py"]


def test_python_host_primitive_support_keeps_generated_executor_skeleton(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)
    support_path = tmp_path / "contracts" / "python_host_primitive_support.py"
    support_path.write_text(
        "from __future__ import annotations\n\n"
        "HOST_SENTINEL = 'host-owned-primitive-support'\n\n"
        "def execute_host_primitive(primitive, *, values, arguments, context):\n"
        "    raise RuntimeError(f'unsupported fixture primitive: {primitive}')\n",
        encoding="utf-8",
    )

    outputs = render_outputs(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        host_manifest={
            "python_primitive_support_path": "contracts/python_host_primitive_support.py",
            "generated_root": "generated",
        },
    )
    rendered = {output.path.relative_to(tmp_path).as_posix(): output.content for output in outputs}

    primitive_executor = rendered["todo_cli_pkg/primitives/primitive_executor.py"]
    support = rendered["todo_cli_pkg/primitives/host_primitive_support.py"]
    assert "Host primitive support: contracts/python_host_primitive_support.py" in primitive_executor
    assert "Portable primitive dispatch and executor structure belong to command-generation." in primitive_executor
    assert "def execute_primitive(" in primitive_executor
    assert "execute_primitive = " not in primitive_executor
    assert "HOST_SENTINEL = 'host-owned-primitive-support'" in support


def test_generated_local_runtime_facade_documents_and_preserves_patch_semantics() -> None:
    source_module = types.ModuleType("fake_source_runtime_for_facade")

    def first_value() -> str:
        return "first"

    setattr(source_module, "runtime_value", first_value)
    sys.modules[source_module.__name__] = source_module
    try:
        rendered = _python_local_runtime_binding_module(
            {
                "program": "demo-cli",
                "python_runtime_binding": {
                    "operation_executor": {
                        "handlers": [
                            {
                                "primitive": "demo.value",
                                "handler": "function_call",
                                "import_module": source_module.__name__,
                                "function": "runtime_value",
                            }
                        ]
                    }
                },
            },
            {
                "source_import_module": source_module.__name__,
                "module_file": "primitives.demo_runtime",
            },
            source_path="demo_ir.json",
            regenerate_command="generate-demo",
        )
        assert "live source-module lookup at call time" in rendered
        assert "not forwarded back into source modules" in rendered
        facade_globals: dict[str, object] = {}
        exec(rendered, facade_globals)

        assert cast(Callable[[], str], facade_globals["runtime_value"])() == "first"

        def second_value() -> str:
            return "second"

        setattr(source_module, "runtime_value", second_value)
        assert cast(Callable[[], str], facade_globals["runtime_value"])() == "second"

        facade_globals["runtime_value"] = lambda: "facade-only"
        assert cast(Callable[[], str], getattr(source_module, "runtime_value"))() == "second"
        assert cast(Callable[[], str], facade_globals["runtime_value"])() == "facade-only"
    finally:
        sys.modules.pop(source_module.__name__, None)


def test_contract_owned_conformance_case_runs_black_box_cli(tmp_path: Path) -> None:
    contract = load_contract_conformance_case("todo.list.process")
    cli = tmp_path / "todo_cli.py"
    cli.write_text(
        "import json\n"
        "import sys\n"
        "if sys.argv[1:] != ['list', '--format', 'json']:\n"
        "    raise SystemExit(2)\n"
        "print(json.dumps({'kind': 'todo-list/v1', 'item_count': 2}))\n",
        encoding="utf-8",
    )
    case = process_case_from_contract(contract=contract, command_placeholder="todo_cli")
    fixture_root = materialize_case_fixture(case=case, root=tmp_path / "fixtures")

    result, failures = run_cli_conformance_case(
        case=case,
        target=CliConformanceTarget(label="python-fixture", command=(sys.executable, str(cli)), cwd=fixture_root),
        fixture_root=fixture_root,
    )

    assert failures == []
    assert result is not None
    assert result.command[-3:] == ("list", "--format", "json")
    assert result.selected_fields == {"kind": "todo-list/v1", "item_count": 2}


def test_contract_owned_conformance_case_reports_output_drift(tmp_path: Path) -> None:
    contract = load_contract_conformance_case("todo.list.process")
    cli = tmp_path / "todo_cli.py"
    cli.write_text("import json\nprint(json.dumps({'kind': 'todo-list/v1', 'item_count': 3}))\n", encoding="utf-8")
    case = process_case_from_contract(contract=contract, command_placeholder="todo_cli")
    fixture_root = materialize_case_fixture(case=case, root=tmp_path / "fixtures")

    _result, failures = run_cli_conformance_case(
        case=case,
        target=CliConformanceTarget(label="python-fixture", command=(sys.executable, str(cli)), cwd=fixture_root),
        fixture_root=fixture_root,
    )

    assert len(failures) == 1
    assert failures[0].conformance_ref == "todo.list.process"
    assert "output shape drifted" in failures[0].message


def test_contract_owned_conformance_case_checks_text_stdout(tmp_path: Path) -> None:
    contract = load_contract_conformance_case("todo.list-text.process")
    cli = tmp_path / "todo_cli.py"
    cli.write_text("print('Todo items:\\n- Write contract-owned test')\n", encoding="utf-8")
    case = process_case_from_contract(contract=contract, command_placeholder="todo_cli")
    fixture_root = materialize_case_fixture(case=case, root=tmp_path / "fixtures")

    result, failures = run_cli_conformance_case(
        case=case,
        target=CliConformanceTarget(label="python-fixture", command=(sys.executable, str(cli)), cwd=fixture_root),
        fixture_root=fixture_root,
    )

    assert failures == []
    assert result is not None
    assert result.stdout == "Todo items:\n- Write contract-owned test\n"


def test_contract_owned_conformance_case_reports_text_stdout_drift(tmp_path: Path) -> None:
    contract = load_contract_conformance_case("todo.list-text.process")
    cli = tmp_path / "todo_cli.py"
    cli.write_text("print('Todo items:\\n- Different item')\n", encoding="utf-8")
    case = process_case_from_contract(contract=contract, command_placeholder="todo_cli")
    fixture_root = materialize_case_fixture(case=case, root=tmp_path / "fixtures")

    _result, failures = run_cli_conformance_case(
        case=case,
        target=CliConformanceTarget(label="python-fixture", command=(sys.executable, str(cli)), cwd=fixture_root),
        fixture_root=fixture_root,
    )

    assert len(failures) == 1
    assert failures[0].conformance_ref == "todo.list-text.process"
    assert "stdout text drifted from contract" in failures[0].message
    assert "- Write contract-owned test" in failures[0].message


def test_contract_owned_operation_case_runs_function_adapter() -> None:
    contract = load_contract_conformance_case("todo.list.operation")
    case = operation_case_from_contract(contract=contract)

    result, failures = run_function_conformance_case(
        case=case,
        target=FunctionConformanceTarget(
            label="python-function",
            invoke=lambda values: {"kind": "todo-list/v1", "item_count": 2, "format": values["format"]},
        ),
    )

    assert failures == []
    assert result is not None
    assert result.selected_fields == {"kind": "todo-list/v1", "item_count": 2}


def test_contract_owned_operation_case_runs_typescript_function_adapter(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for TypeScript function conformance")
    manifest = _fixture_manifest_with_typescript(tmp_path)

    stale = generate_command_packages(
        manifest,
        repo_root=tmp_path,
        source_path="command_package_ir.json",
        regenerate_command="python generate.py",
        check=False,
    )
    contract = load_contract_conformance_case("todo.list.operation")
    case = operation_case_from_contract(contract=contract)

    result, failures = run_typescript_function_conformance_case(
        case=case,
        target=TypescriptFunctionConformanceTarget(
            label="typescript-function",
            runtime_path=tmp_path / "todo_ts_pkg" / "src" / "runtime.mjs",
            operation_id="todo.list.report",
            operation_path="operations/todo.list.report.json",
            cwd=tmp_path,
        ),
    )

    assert stale == []
    assert failures == []
    assert result is not None
    assert result.selected_fields == {"kind": "todo-list/v1", "item_count": 2}


def test_contract_owned_operation_case_reports_function_output_drift() -> None:
    contract = load_contract_conformance_case("todo.list.operation")
    case = operation_case_from_contract(contract=contract)

    _result, failures = run_function_conformance_case(
        case=case,
        target=FunctionConformanceTarget(
            label="python-function",
            invoke=lambda _values: {"kind": "todo-list/v1", "item_count": 3},
        ),
    )

    assert len(failures) == 1
    assert failures[0].conformance_ref == "todo.list.operation"
    assert "result shape drifted" in failures[0].message


def test_contract_owned_operation_case_checks_expected_function_error() -> None:
    contract = load_contract_conformance_case("todo.list-error.operation")
    case = operation_case_from_contract(contract=contract)

    result, failures = run_function_conformance_case(
        case=case,
        target=FunctionConformanceTarget(
            label="python-function",
            invoke=lambda _values: (_ for _ in ()).throw(ValueError("invalid format: yaml")),
        ),
    )

    assert failures == []
    assert result is not None
    assert "invalid format" in result.error


def test_conformance_ownership_inventory_accounts_for_shared_and_consumer_surfaces() -> None:
    inventory = conformance_ownership_inventory()

    owns = cast(list[Mapping[str, object]], inventory["owns"])
    owned = {entry["id"] for entry in owns}
    assert {
        "process-conformance-runner",
        "function-operation-conformance-runner",
        "generated-artifact-freshness",
        "operation-ir-primitives",
        "bundled-conformance-case-resources",
    } <= owned
    assert "FunctionConformanceTarget" in cast(list[str], inventory["extension_points"])
    assert "TypescriptFunctionConformanceTarget" in cast(list[str], inventory["extension_points"])
    assert "consumer proof routing and installed-package lifecycle tests" in cast(list[str], inventory["consumer_owned"])
    assert "consumer-specific behavior remains in the consumer repo" in str(inventory["completion_rule"])


def test_contract_conformance_cases_manifest_loads_package_owned_cases() -> None:
    manifest = contract_conformance_cases_manifest()
    contracts = cast(list[Mapping[str, object]], manifest["contracts"])
    cases = {entry["id"]: entry for entry in contracts}

    assert manifest["schema_version"] == "command-generation/conformance-cases/v1"
    assert cases["todo.list.process"]["category"] == "convert"
    assert load_contract_conformance_case("todo.list.operation")["operation_id"] == "todo.list.report"


def test_generated_output_freshness_report_counts_hashes_and_staleness_by_host_target_family(tmp_path: Path) -> None:
    py_path = tmp_path / "out" / "python" / "cli.py"
    ts_path = tmp_path / "out" / "typescript" / "cli.mjs"
    py_path.parent.mkdir(parents=True)
    ts_path.parent.mkdir(parents=True)
    py_path.write_text("print('fresh')\n", encoding="utf-8")
    ts_path.write_text("stale\n", encoding="utf-8")

    report = generated_output_freshness_report(
        [
            GeneratedOutput(path=py_path, content="print('fresh')\n"),
            GeneratedOutput(path=ts_path, content="console.log('fresh');\n"),
        ],
        repo_root=tmp_path,
        required_target_families=("python", "typescript"),
        target_family_for_path=lambda path: path.parent.name,
    )

    assert report["status"] == "stale-or-incomplete"
    assert report["rendered_output_count_by_family"] == {"python": 1, "typescript": 1}
    assert report["stale_output_count_by_family"] == {"typescript": 1}
    assert report["stale_outputs_by_family"] == {"typescript": ["out/typescript/cli.mjs"]}
    assert report["missing_target_families"] == []
    assert set(report["expected_digest_by_family"]) == {"python", "typescript"}
    assert "do not rewrite generated files" in report["cheap_check_rule"]


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


def test_generator_delegates_to_internal_target_renderers() -> None:
    generator_source = (Path(__file__).resolve().parents[1] / "src" / "command_generation" / "generator.py").read_text(
        encoding="utf-8"
    )
    python_target = importlib.import_module("command_generation.targets.python")
    typescript_target = importlib.import_module("command_generation.targets.typescript")

    assert callable(python_target.render_python_outputs)
    assert callable(typescript_target.render_typescript_outputs)
    assert "render_python_outputs" in generator_source
    assert "render_typescript_outputs" in generator_source
    assert "def _python_runtime_adapter_module" not in generator_source
    assert "def _typescript_runtime_module" not in generator_source


def test_payload_assemble_builds_declarative_package_file_list(tmp_path: Path) -> None:
    result = execute_primitive(
        "payload.assemble",
        values={
            "files": [{"relative_path": "required.md"}, {"relative_path": "optional.md"}],
            "skill_files": [{"relative_path": "fixture-skill/SKILL.md"}],
        },
        arguments={
            "fields": {
                "payload_kind": "package-file-list",
                "files_from": "files",
                "bundled_skill_files_from": "skill_files",
                "default_files": ["required.md"],
                "optional_files": ["optional.md"],
                "optional_enable_commands": ["fixturectl install --include-optional"],
            }
        },
        context=PrimitiveContext(cwd=tmp_path),
    )

    assert result == {
        "files": ["required.md", "optional.md"],
        "default_files": ["required.md"],
        "optional_files": ["optional.md"],
        "bundled_skill_files": ["fixture-skill/SKILL.md"],
        "optional_enable_commands": ["fixturectl install --include-optional"],
    }


def test_output_emit_renders_file_lists_as_text_lines(tmp_path: Path) -> None:
    result = execute_primitive(
        "output.emit",
        values={"format": "text", "result": {"files": ["required.md", "optional.md"]}},
        arguments={},
        context=PrimitiveContext(cwd=tmp_path),
    )

    assert result == "required.md\noptional.md\n"


def test_generic_primitive_executor_has_no_aw_path_literals() -> None:
    source = (Path(__file__).resolve().parents[1] / "src" / "command_generation" / "primitive_executor.py").read_text(
        encoding="utf-8"
    )

    assert ".agentic-workspace" not in source


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


def test_primitive_registry_checks_steps_inside_fragments(tmp_path: Path) -> None:
    manifest = _fixture_manifest(tmp_path)
    operation_path = tmp_path / "contracts" / "operations" / "todo.list.report.json"
    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    read_step = operation["ir_plan"]["steps"].pop(0)
    operation["ir_plan"]["fragments"] = [
        {
            "id": "load-todos",
            "description": "Load todo source data.",
            "steps": [read_step],
        }
    ]
    operation["ir_plan"]["steps"].insert(
        0,
        {
            "id": "load",
            "uses_fragment": "load-todos",
            "description": "Load todo data through a fragment.",
        },
    )
    operation_path.write_text(json.dumps(operation, indent=2), encoding="utf-8")
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

    with pytest.raises(ValueError, match="filesystem.read"):
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
                "kind": "host-owned",
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


def test_builtin_registry_classifies_primitive_ownership_boundaries() -> None:
    definitions = {item["id"]: item for item in BUILTIN_PORTABLE_PRIMITIVES.to_jsonable()}

    assert {item["kind"] for item in definitions.values()} <= {"portable", "host-owned", "transitional"}
    assert definitions["filesystem.read"]["kind"] == "portable"
    assert definitions["json.parse"]["kind"] == "portable"
    assert definitions["payload.status"]["kind"] == "transitional"
    assert definitions["payload.verify"]["kind"] == "transitional"
    assert definitions["payload.current-memory"]["kind"] == "transitional"
    assert definitions["output.emit.current-memory"]["kind"] == "transitional"
    assert definitions["python.function.call"]["kind"] == "host-owned"
    assert definitions["typescript.domain.execute"]["kind"] == "host-owned"

    transitional = [item for item in definitions.values() if item["kind"] == "transitional"]
    assert transitional
    assert all(item["owner"] == "host" for item in transitional)
    assert all(item["description"] for item in definitions.values())


def test_transitional_primitives_declare_retirement_policy() -> None:
    definitions = {item["id"]: item for item in BUILTIN_PORTABLE_PRIMITIVES.to_jsonable()}
    transitional = {primitive_id: item for primitive_id, item in definitions.items() if item["kind"] == "transitional"}

    assert set(transitional) == {
        "workspace.root.resolve",
        "payload.status",
        "payload.lifecycle-plan",
        "payload.current-memory",
        "payload.verify",
        "output.emit.install-result",
        "output.emit.current-memory",
    }
    for primitive in transitional.values():
        retirement = primitive["transitional_retirement"]
        assert set(retirement) == {
            "target_end_state",
            "rationale",
            "migration_note",
            "compatibility",
            "coordination_issue",
        }
        assert retirement["coordination_issue"] == "https://github.com/rickardvh/command-generation/issues/44"
        assert retirement["target_end_state"] in {
            "renamed/reshaped portable behavior",
            "host-owned registry behavior",
            "removed after downstream migration",
            "retained with generic rationale",
        }
        assert "AW" in retirement["migration_note"] or "path.target_root.resolve" in retirement["migration_note"]


def test_transitional_primitives_require_owner_and_retirement_metadata() -> None:
    missing_retirement = {
        "id": "fixture.transitional",
        "kind": "transitional",
        "owner": "host",
        "description": "Fixture transitional primitive.",
        "target_support": {"python": "implemented"},
    }
    missing_owner = {
        **missing_retirement,
        "transitional_retirement": {
            "target_end_state": "host-owned registry behavior",
            "rationale": "Fixture rationale.",
            "migration_note": "Move to a fixture-owned primitive.",
            "compatibility": "Retain until fixture migration completes.",
            "coordination_issue": "https://github.com/example/repo/issues/1",
        },
    }

    with pytest.raises(ValueError, match="transitional_retirement fields"):
        PrimitiveRegistry.from_definitions([missing_retirement])
    with pytest.raises(ValueError, match="must declare the host or migration owner"):
        PrimitiveRegistry.from_definitions([{**missing_owner, "owner": "command-generation"}])


def _target_extension_contract(**overrides: object) -> dict[str, object]:
    contract: dict[str, object] = {
        "schema_version": "command-generation/target-extension/v1",
        "target_id": "python",
        "implementation_status": "implemented",
        "projection_rules": {
            "source": "operation-ir",
            "target_owns": ["syntax projection", "runtime imports"],
        },
        "runtime_dependencies": {
            "boundary": ["standard library json", "generated package resources"],
        },
        "operation_callable_surface": {
            "adapter_id": "python.function",
            "input_model": "operation-values",
            "structured_errors": True,
        },
        "wrapper_adapter_shape": {
            "owns": ["argv parsing", "exit-code mapping"],
        },
        "packaging_output_layout": {
            "owns": ["module path", "resource layout"],
        },
        "conformance_execution": {
            "runner": "function",
            "case_model": "input-output-error",
        },
        "support_declaration": {
            "matrix_inclusion": "automatic-when-target-implemented",
            "adapter_ids": ["python.function"],
        },
        "product_semantics_boundary": {
            "target_owns_product_semantics": False,
            "rule": "Product behavior remains in operation IR, primitive refs, and host-owned runtime primitives.",
        },
        "maintenance_boundary": {
            "per_operation_feature_maintenance": False,
            "allowed": ["runtime dependency updates", "target compatibility fixes", "projection bugs"],
        },
    }
    contract.update(overrides)
    return contract


def _typescript_target_extension_contract() -> dict[str, object]:
    return _target_extension_contract(
        target_id="typescript",
        operation_callable_surface={
            "adapter_id": "typescript.function",
            "input_model": "operation-values",
            "structured_errors": False,
        },
        wrapper_adapter_shape={
            "owns": ["argv parsing", "exit-code mapping"],
        },
        support_declaration={
            "matrix_inclusion": "automatic-when-target-implemented",
            "adapter_ids": ["typescript.function"],
            "primitive_support": "declared",
        },
    )


def test_target_extension_contract_validates_and_projects_matrix_entries() -> None:
    contract = TargetExtensionContract.from_mapping(_target_extension_contract())

    assert target_extension_schema_path().name == "target_extension.schema.json"
    assert contract.target_id == "python"
    assert target_support_matrix_entries(
        [contract],
        operation_id="todo.list.report",
        case_id="todo.list.operation",
    ) == (
        {
            "operation_id": "todo.list.report",
            "case_id": "todo.list.operation",
            "target_id": "python",
            "adapter_id": "python.function",
            "source": "target-extension support declaration",
        },
    )


def test_required_target_proof_matrix_requires_evidence_for_implemented_targets() -> None:
    required = required_target_proof_matrix_entries([_target_extension_contract(), _typescript_target_extension_contract()])
    evidence_inventory = current_target_proof_evidence_inventory()
    evidence_ids = {item["evidence_id"] for item in evidence_inventory}

    assert {entry["proof_kind"] for entry in required} == {
        "direct-operation-success",
        "direct-operation-structured-error",
        "cli-process-success",
        "cli-process-parser-failure",
        "generated-artifact-freshness",
        "generated-runtime-boundary",
        "unsupported-primitive-target",
    }
    assert {entry["surface"] for entry in required} == {
        "function",
        "process",
        "freshness",
        "runtime-boundary",
        "primitive-support",
    }
    assert all(item["source"].startswith("tests/test_public_api.py::test_") for item in evidence_inventory)
    assert missing_target_proof_matrix_entries(required, evidence_ids) == ()


def test_structured_target_proof_evidence_inventory_types_current_evidence() -> None:
    required = required_target_proof_matrix_entries([_target_extension_contract(), _typescript_target_extension_contract()])
    required_by_id = {entry["evidence_id"]: entry for entry in required}
    structured = structured_target_proof_evidence_inventory()
    flat = current_target_proof_evidence_inventory()

    assert {item["evidence_id"] for item in structured} == set(required_by_id)
    assert flat == tuple({"evidence_id": item["evidence_id"], "source": item["source"]} for item in structured)
    assert {item["evidence_type"] for item in structured} == {
        "conformance-case",
        "ordinary-test",
        "source-guard",
        "freshness-check",
    }
    for item in structured:
        assert item["surface"] == required_by_id[item["evidence_id"]]["surface"]
        assert item["target_id"] == required_by_id[item["evidence_id"]]["target_id"]
        assert item["adapter_id"] == required_by_id[item["evidence_id"]]["adapter_id"]
        assert item["proof_kind"] == required_by_id[item["evidence_id"]]["proof_kind"]


def test_required_target_proof_matrix_reports_missing_evidence() -> None:
    required = required_target_proof_matrix_entries([_target_extension_contract()])

    missing = missing_target_proof_matrix_entries(required, {"python:python.function:direct-operation-success"})

    assert {entry["proof_kind"] for entry in missing} == {
        "direct-operation-structured-error",
        "cli-process-success",
        "cli-process-parser-failure",
        "generated-artifact-freshness",
        "generated-runtime-boundary",
        "unsupported-primitive-target",
    }
    assert all(entry["surface"] for entry in missing)
    assert missing[0]["evidence_id"].startswith("python:python.function:")


def test_target_extension_support_matrix_waits_for_implemented_target() -> None:
    assert (
        target_support_matrix_entries(
            [_target_extension_contract(implementation_status="planned")],
            operation_id="todo.list.report",
            case_id="todo.list.operation",
        )
        == ()
    )


def test_target_extension_contract_rejects_product_semantics_ownership() -> None:
    contract = _target_extension_contract(
        product_semantics_boundary={
            "target_owns_product_semantics": True,
            "rule": "bad target owns behavior",
        }
    )

    with pytest.raises(TargetExtensionContractError, match="target_owns_product_semantics"):
        validate_target_extension_contract(contract)


def test_target_extension_contract_rejects_per_operation_feature_maintenance() -> None:
    contract = _target_extension_contract(
        maintenance_boundary={
            "per_operation_feature_maintenance": True,
            "allowed": ["add feature logic in each target"],
        }
    )

    with pytest.raises(TargetExtensionContractError, match="per_operation_feature_maintenance"):
        validate_target_extension_contract(contract)
