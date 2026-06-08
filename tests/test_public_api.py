from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from command_generation import (
    BUILTIN_PORTABLE_PRIMITIVES,
    CliConformanceTarget,
    CommandGenerationHostManifest,
    GeneratedOutput,
    PrimitiveContext,
    PrimitiveRegistry,
    command_package_schema_path,
    execute_primitive,
    generate_command_packages,
    generated_output_freshness_report,
    load_command_package_ir,
    materialize_case_fixture,
    process_case_from_contract,
    render_outputs,
    run_cli_conformance_case,
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


def test_contract_owned_conformance_case_runs_black_box_cli(tmp_path: Path) -> None:
    contract = {
        "id": "todo.list.process",
        "operation_id": "todo.list.report",
        "adapter": {
            "kind": "process",
            "command_template": ["{todo_cli}", "list", "--format", "json"],
            "cwd": "fixture_root",
        },
        "fixtures": [
            {
                "id": "minimal-repo",
                "files": {"README.md": "# Fixture\n"},
            }
        ],
        "expectations": {
            "exit": {"code": 0},
            "stdout": {
                "format": "json",
                "field_assertions": [
                    {"path": ["kind"], "equals": "todo-list/v1"},
                    {"path": ["item_count"], "equals": 2},
                ],
            },
            "stderr": {"allow_non_empty": False},
        },
    }
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
    contract = {
        "id": "todo.list.process",
        "operation_id": "todo.list.report",
        "adapter": {
            "kind": "process",
            "command_template": ["{todo_cli}", "list", "--format", "json"],
            "cwd": "fixture_root",
        },
        "fixtures": [{"id": "minimal-repo", "files": {}}],
        "expectations": {
            "exit": {"code": 0},
            "stdout": {
                "format": "json",
                "field_assertions": [{"path": ["item_count"], "equals": 2}],
            },
            "stderr": {"allow_non_empty": False},
        },
    }
    cli = tmp_path / "todo_cli.py"
    cli.write_text("import json\nprint(json.dumps({'item_count': 3}))\n", encoding="utf-8")
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
    contract = {
        "id": "todo.list-text.process",
        "operation_id": "todo.list.report",
        "adapter": {
            "kind": "process",
            "command_template": ["{todo_cli}", "list", "--format", "text"],
            "cwd": "fixture_root",
        },
        "fixtures": [{"id": "minimal-repo", "files": {}}],
        "expectations": {
            "exit": {"code": 0},
            "stdout": {
                "format": "text",
                "field_assertions": [],
                "contains": ["Todo items:", "- Write contract-owned test"],
            },
            "stderr": {"allow_non_empty": False},
        },
    }
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
    contract = {
        "id": "todo.list-text.process",
        "operation_id": "todo.list.report",
        "adapter": {
            "kind": "process",
            "command_template": ["{todo_cli}", "list", "--format", "text"],
            "cwd": "fixture_root",
        },
        "fixtures": [{"id": "minimal-repo", "files": {}}],
        "expectations": {
            "exit": {"code": 0},
            "stdout": {
                "format": "text",
                "field_assertions": [],
                "contains": ["Todo items:", "- Write contract-owned test"],
            },
            "stderr": {"allow_non_empty": False},
        },
    }
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
