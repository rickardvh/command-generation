from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import pytest

from command_generation.primitive_executor import (
    PrimitiveContext,
    PrimitiveExecutionError,
    execute_primitive,
    run_operation_steps,
)


@pytest.fixture()
def primitive_context(tmp_path: Path) -> PrimitiveContext:
    package_root = tmp_path / "package"
    package_root.mkdir()
    (package_root / "alpha.txt").write_text("alpha", encoding="utf-8")
    (package_root / "nested").mkdir()
    (package_root / "nested" / "beta.txt").write_text("beta", encoding="utf-8")
    (package_root / "REGISTRY.json").write_text(
        json.dumps({"skills": [{"id": "review", "path": "review/SKILL.md"}]}),
        encoding="utf-8",
    )
    (tmp_path / "target").mkdir()
    return PrimitiveContext(cwd=tmp_path, roots={"package": package_root})


def test_path_target_root_resolve_uses_context_cwd(primitive_context: PrimitiveContext) -> None:
    target_root = execute_primitive(
        "path.target_root.resolve",
        values={"target": "target"},
        context=primitive_context,
    )

    assert target_root == str((primitive_context.cwd / "target").resolve())


def test_filesystem_read_is_rooted(primitive_context: PrimitiveContext) -> None:
    assert (
        execute_primitive(
            "filesystem.read",
            values={},
            arguments={"root": "package", "path": "REGISTRY.json"},
            context=primitive_context,
        )
        == '{"skills": [{"id": "review", "path": "review/SKILL.md"}]}'
    )

    with pytest.raises(PrimitiveExecutionError, match="path escapes primitive root"):
        execute_primitive(
            "filesystem.read",
            values={},
            arguments={"root": "package", "path": "../escape.txt"},
            context=primitive_context,
        )


def test_filesystem_glob_returns_stable_relative_files(primitive_context: PrimitiveContext) -> None:
    files = execute_primitive(
        "filesystem.glob",
        values={},
        arguments={"root": "package", "pattern": "**/*.txt"},
        context=primitive_context,
    )

    assert files == [{"relative_path": "alpha.txt"}, {"relative_path": "nested/beta.txt"}]


def test_filesystem_primitives_can_use_value_roots(primitive_context: PrimitiveContext) -> None:
    target = primitive_context.cwd / "target"
    (target / "feedback.md").write_text("ok", encoding="utf-8")
    (target / "fixtures").mkdir()
    (target / "fixtures" / "case.json").write_text("{}", encoding="utf-8")

    values = {"target_root": str(target)}

    assert execute_primitive(
        "filesystem.exists",
        values=values,
        arguments={"base_value": "target_root", "path": "feedback.md", "kind": "file"},
        context=primitive_context,
    )
    assert execute_primitive(
        "filesystem.glob",
        values=values,
        arguments={"base_value": "target_root", "pattern": "fixtures/*.json"},
        context=primitive_context,
    ) == [{"relative_path": "fixtures/case.json"}]


def test_json_parse_uses_named_source_value(primitive_context: PrimitiveContext) -> None:
    registry = execute_primitive(
        "json.parse",
        values={"registry_text": '{"skills": [{"id": "review"}]}'},
        context=primitive_context,
    )

    assert registry == {"skills": [{"id": "review"}]}


def test_toml_table_counts_returns_stable_counts(primitive_context: PrimitiveContext) -> None:
    target = primitive_context.cwd / "target"
    manifest = target / ".agentic-workspace" / "memory" / "repo"
    manifest.mkdir(parents=True)
    (manifest / "manifest.toml").write_text(
        "\n".join(
            [
                "[notes.required]",
                'task_relevance = "required"',
                "[notes.optional]",
                'task_relevance = "optional"',
                "routing_only = true",
            ]
        ),
        encoding="utf-8",
    )

    result = execute_primitive(
        "toml.table.counts",
        values={"target_root": str(target)},
        arguments={
            "base_value": "target_root",
            "path": ".agentic-workspace/memory/repo/manifest.toml",
            "table": "notes",
            "relevance_field": "task_relevance",
            "required_value": "required",
            "optional_value": "optional",
            "routing_only_field": "routing_only",
        },
        context=primitive_context,
    )

    assert result == {
        "table_counts": {
            "status": "present",
            "note_count": 2,
            "required_count": 1,
            "optional_count": 1,
            "routing_only_count": 1,
            "path": ".agentic-workspace/memory/repo/manifest.toml",
        },
        "table_present": True,
        "table_status": "present",
    }


def test_toml_table_counts_reports_missing_file(primitive_context: PrimitiveContext) -> None:
    result = execute_primitive(
        "toml.table.counts",
        values={"target_root": str(primitive_context.cwd / "target")},
        arguments={"base_value": "target_root", "path": "missing.toml", "table": "notes"},
        context=primitive_context,
    )

    assert result["table_counts"]["status"] == "missing"
    assert result["table_present"] is False
    assert result["table_status"] == "missing"


def test_payload_assemble_supports_file_and_skill_records(primitive_context: PrimitiveContext) -> None:
    file_payload = execute_primitive(
        "payload.assemble",
        values={
            "target_root": str((primitive_context.cwd / "target").resolve()),
            "files": [{"relative_path": "alpha.txt"}],
        },
        arguments={"fields": {"dry_run": True, "message": "Files", "actions_from": "files"}},
        context=primitive_context,
    )
    skill_payload = execute_primitive(
        "payload.assemble",
        values={"registry": {"skills": [{"id": "review", "path": "review/SKILL.md"}]}},
        arguments={
            "fields": {
                "dry_run": True,
                "message": "Skills",
                "actions_from": "registry.skills",
                "mode": "skills",
                "bootstrap_version_from": "bootstrap_version",
            }
        },
        context=primitive_context,
    )

    assert file_payload["actions"] == [{"kind": "file", "path": "alpha.txt"}]
    assert skill_payload["mode"] == "skills"
    assert skill_payload["actions"][0]["kind"] == "bundled skill"
    assert skill_payload["actions"][0]["path"] == "review"


def test_payload_assemble_supports_template_records(primitive_context: PrimitiveContext) -> None:
    payload = execute_primitive(
        "payload.assemble",
        values={
            "target_root": str((primitive_context.cwd / "target").resolve()),
            "feedback_exists": True,
            "fixture_files": [{"relative_path": "fixtures/case.json"}],
        },
        arguments={
            "fields": {
                "template": {
                    "target_root": {"$value": "target_root"},
                    "route_report_summary": {
                        "feedback": {
                            "status": {"$exists_status": {"value": "feedback_exists", "present": "present", "missing": "missing"}},
                            "path": {"$join_path": {"base": "target_root", "path": "feedback.md"}},
                        },
                        "fixtures": {
                            "status": {"$count_status": {"value": "fixture_files", "present": "present", "missing": "missing"}},
                            "fixture_count": {"$count": "fixture_files"},
                        },
                    },
                }
            }
        },
        context=primitive_context,
    )

    assert payload["route_report_summary"]["feedback"]["status"] == "present"
    assert payload["route_report_summary"]["fixtures"]["fixture_count"] == 1


def test_payload_assemble_supports_template_field_selectors(primitive_context: PrimitiveContext) -> None:
    payload = execute_primitive(
        "payload.assemble",
        values={
            "table_counts": {
                "status": "present",
                "note_count": 3,
                "required_count": 1,
            }
        },
        arguments={
            "fields": {
                "template": {
                    "status": {"$field": {"value": "table_counts", "path": "status"}},
                    "nested": {
                        "note_count": {"$field": {"value": "table_counts", "path": ["note_count"]}},
                        "required_count": {"$field": {"value": "table_counts", "path": "required_count"}},
                    },
                }
            }
        },
        context=primitive_context,
    )

    assert payload == {"status": "present", "nested": {"note_count": 3, "required_count": 1}}


def test_payload_project_selects_exact_paths_and_reports_missing(primitive_context: PrimitiveContext) -> None:
    result = execute_primitive(
        "payload.project",
        values={
            "operation_id": "fixture.show",
            "select": "items.0.name,summary.count,missing.value",
            "result": {
                "summary": {"count": 2},
                "items": [{"name": "alpha"}, {"name": "beta"}],
            },
        },
        context=primitive_context,
    )

    assert result["kind"] == "command-generation/selected-output/v1"
    assert result["source_command"] == "fixture.show"
    assert result["values"] == {"items.0.name": "alpha", "summary.count": 2}
    assert result["missing"] == ["missing.value"]
    assert "items.1.name" in result["available_selectors"]


def test_payload_project_can_use_declared_selector_list(primitive_context: PrimitiveContext) -> None:
    result = execute_primitive(
        "payload.project",
        values={
            "payload": {
                "status": "ready",
                "details": {"owner": "fixture"},
            }
        },
        arguments={
            "source": "payload",
            "source_command": "fixture.status",
            "selectors": ["status", "details.owner"],
            "selected_output_kind": "fixture/selected-output/v1",
        },
        context=primitive_context,
    )

    assert result == {
        "kind": "fixture/selected-output/v1",
        "source_command": "fixture.status",
        "values": {"status": "ready", "details.owner": "fixture"},
    }


def test_operation_fragments_compose_reusable_step_groups(primitive_context: PrimitiveContext) -> None:
    operation = {
        "id": "fixture.report",
        "ir_plan": {
            "fragments": [
                {
                    "id": "load-fixture",
                    "steps": [
                        {
                            "id": "make_result",
                            "uses": "fixture.make-result",
                            "description": "Create a fixture payload.",
                            "outputs": ["result"],
                        }
                    ],
                }
            ],
            "steps": [
                {
                    "id": "load",
                    "uses_fragment": "load-fixture",
                    "description": "Reuse the fixture loading fragment.",
                },
                {
                    "id": "emit",
                    "uses": "output.emit",
                    "description": "Emit the fixture payload.",
                    "outputs": ["emitted"],
                },
            ],
        },
    }

    values = run_operation_steps(
        operation,
        initial_values={"format": "json"},
        context=primitive_context,
        handlers={"fixture.make-result": lambda values, arguments, context: {"status": "ok"}},
    )

    assert json.loads(values["emitted"]) == {"status": "ok"}


def test_run_operation_steps_can_project_payload_fields(primitive_context: PrimitiveContext) -> None:
    operation = {
        "id": "fixture.project",
        "ir_plan": {
            "steps": [
                {
                    "id": "make_result",
                    "uses": "fixture.make-result",
                    "outputs": ["result"],
                },
                {
                    "id": "project",
                    "uses": "payload.project",
                    "arguments": {
                        "selectors": ["summary.status"],
                        "source_command": "fixture.project",
                    },
                    "outputs": ["selected"],
                },
            ]
        },
    }

    values = run_operation_steps(
        operation,
        initial_values={},
        context=primitive_context,
        handlers={"fixture.make-result": lambda values, arguments, context: {"summary": {"status": "ready"}}},
    )

    assert values["selected"]["values"] == {"summary.status": "ready"}


def test_operation_fragments_reject_cycles(primitive_context: PrimitiveContext) -> None:
    operation = {
        "id": "fixture.report",
        "ir_plan": {
            "fragments": [
                {"id": "a", "steps": [{"id": "call_b", "uses_fragment": "b", "description": "Call b."}]},
                {"id": "b", "steps": [{"id": "call_a", "uses_fragment": "a", "description": "Call a."}]},
            ],
            "steps": [{"id": "call_a", "uses_fragment": "a", "description": "Call a."}],
        },
    }

    with pytest.raises(PrimitiveExecutionError, match="operation ir_plan fragment cycle: a -> b -> a"):
        run_operation_steps(operation, initial_values={}, context=primitive_context)


def test_output_emit_supports_json_and_text(primitive_context: PrimitiveContext) -> None:
    payload = {
        "dry_run": True,
        "message": "Skills",
        "actions": [{"kind": "skill", "id": "review", "path": "review/SKILL.md"}],
    }

    emitted_json = execute_primitive("output.emit", values={"result": payload, "format": "json"}, context=primitive_context)
    emitted_text = execute_primitive("output.emit", values={"result": payload, "format": "text"}, context=primitive_context)

    assert json.loads(emitted_json)["actions"][0]["id"] == "review"
    assert emitted_text == "Skills\n- review/SKILL.md\n"


def test_output_emit_serializes_module_result_objects(primitive_context: PrimitiveContext) -> None:
    @dataclass
    class Action:
        kind: str
        path: Path

    @dataclass
    class DataclassResult:
        dry_run: bool
        message: str
        actions: list[Action]

    @dataclass
    class ContractResult:
        raw_path: Path

        def to_dict(self) -> dict[str, object]:
            return {"path": "contract-owned/path.md"}

    class ModuleResult:
        def to_dict(self) -> dict[str, object]:
            return {
                "dry_run": False,
                "message": "Installed",
                "target_root": primitive_context.cwd,
                "actions": [{"kind": "create", "path": "AGENTS.md"}],
            }

    emitted_json = execute_primitive("output.emit", values={"result": ModuleResult(), "format": "json"}, context=primitive_context)
    emitted_text = execute_primitive("output.emit", values={"result": ModuleResult(), "format": "text"}, context=primitive_context)

    emitted_payload = json.loads(emitted_json)
    assert emitted_payload["actions"][0]["path"] == "AGENTS.md"
    assert emitted_payload["target_root"] == str(primitive_context.cwd)
    assert "Installed" in emitted_text
    assert "- AGENTS.md" in emitted_text

    dataclass_json = execute_primitive(
        "output.emit",
        values={
            "result": DataclassResult(False, "Planned", [Action("create", primitive_context.cwd / "plan.md")]),
            "format": "json",
        },
        context=primitive_context,
    )
    assert json.loads(dataclass_json)["actions"][0]["path"] == str(primitive_context.cwd / "plan.md")

    contract_json = execute_primitive(
        "output.emit",
        values={"result": ContractResult(primitive_context.cwd / "raw.md"), "format": "json"},
        context=primitive_context,
    )
    assert json.loads(contract_json)["path"] == "contract-owned/path.md"


def test_removed_transitional_primitives_are_not_generic_executor_behavior(primitive_context: PrimitiveContext) -> None:
    for primitive in (
        "workspace.root.resolve",
        "payload.status",
        "payload.lifecycle-plan",
        "payload.current-memory",
        "payload.verify",
        "output.emit.install-result",
        "output.emit.current-memory",
    ):
        with pytest.raises(PrimitiveExecutionError, match="unsupported host primitive"):
            execute_primitive(primitive, values={"result": {}}, context=primitive_context)


def test_python_function_call_resolves_checked_in_arguments(primitive_context: PrimitiveContext) -> None:
    result = execute_primitive(
        "python.function.call",
        values={"payload_text": '{"status": "ok"}'},
        arguments={
            "import_module": "json",
            "function": "loads",
            "kwargs": {
                "s": {"value": "payload_text"},
            },
        },
        context=primitive_context,
    )

    assert result == {"status": "ok"}


def test_operation_call_maps_positional_keyword_and_coerced_values(primitive_context: PrimitiveContext) -> None:
    runtime_module = types.ModuleType("fixture_operation_runtime")
    calls: list[dict[str, object]] = []

    def archive_operation(
        target: str,
        payload: dict[str, object],
        *,
        dry_run: bool,
        retain_archive: bool,
        mode: str,
    ) -> dict[str, object]:
        call = {
            "target": target,
            "payload": payload,
            "dry_run": dry_run,
            "retain_archive": retain_archive,
            "mode": mode,
        }
        calls.append(call)
        return call

    setattr(runtime_module, "archive_operation", archive_operation)
    sys.modules[runtime_module.__name__] = runtime_module
    try:
        result = execute_primitive(
            "operation.call",
            values={
                "target": "",
                "payload": {"id": "P1"},
                "dry_run": "yes",
                "discard_archive": True,
            },
            arguments={
                "import_module": runtime_module.__name__,
                "function": "archive_operation",
                "args": [
                    {"string_value": "target", "default": "."},
                    {"raw_value": "payload"},
                ],
                "kwargs": {
                    "dry_run": {"bool_value": "dry_run"},
                    "retain_archive": {"not_bool_value": "discard_archive"},
                    "mode": {"literal": "fast"},
                },
            },
            context=primitive_context,
        )
    finally:
        sys.modules.pop(runtime_module.__name__, None)

    assert result == {
        "target": ".",
        "payload": {"id": "P1"},
        "dry_run": True,
        "retain_archive": False,
        "mode": "fast",
    }
    assert calls == [result]


def test_python_function_call_rejects_unresolved_targets(primitive_context: PrimitiveContext) -> None:
    with pytest.raises(PrimitiveExecutionError, match="cannot resolve"):
        execute_primitive(
            "python.function.call",
            values={},
            arguments={"import_module": "json", "function": "missing_function", "kwargs": {}},
            context=primitive_context,
        )


def test_python_function_call_rejects_missing_value_bindings(primitive_context: PrimitiveContext) -> None:
    with pytest.raises(PrimitiveExecutionError, match="cannot resolve value"):
        execute_primitive(
            "python.function.call",
            values={},
            arguments={
                "import_module": "json",
                "function": "loads",
                "kwargs": {"s": {"value": "missing"}},
            },
            context=primitive_context,
        )


def test_run_operation_steps_executes_declared_dataflow(primitive_context: PrimitiveContext) -> None:
    operation = {
        "ir_plan": {
            "steps": [
                {
                    "id": "read_registry",
                    "uses": "filesystem.read",
                    "arguments": {"root": "package", "path": "REGISTRY.json"},
                    "outputs": ["registry_text"],
                },
                {"id": "parse_registry", "uses": "json.parse", "outputs": ["registry"]},
                {
                    "id": "assemble",
                    "uses": "payload.assemble",
                    "arguments": {"fields": {"dry_run": True, "message": "Skills", "actions_from": "registry.skills"}},
                    "outputs": ["result"],
                },
                {"id": "emit", "uses": "output.emit", "outputs": ["emitted"]},
            ]
        }
    }

    values = run_operation_steps(operation, initial_values={"format": "json"}, context=primitive_context)

    assert json.loads(values["emitted"])["actions"][0]["source"] == "review"


def test_run_operation_steps_honors_simple_when_conditions(primitive_context: PrimitiveContext) -> None:
    operation = {
        "ir_plan": {
            "steps": [
                {
                    "id": "skip_text",
                    "uses": "payload.assemble",
                    "when": {"value": "format", "equals": "text"},
                    "arguments": {"fields": {"dry_run": True, "message": "Text", "actions_from": "files"}},
                    "outputs": ["result"],
                },
                {
                    "id": "emit_json",
                    "uses": "payload.assemble",
                    "when": {"all": [{"value": "format", "equals": "json"}, {"not": {"value": "verbose", "equals": True}}]},
                    "arguments": {"fields": {"template": {"message": "JSON"}}},
                    "outputs": ["result"],
                },
            ]
        }
    }

    values = run_operation_steps(operation, initial_values={"format": "json", "verbose": False}, context=primitive_context)

    assert values["result"] == {"message": "JSON"}
