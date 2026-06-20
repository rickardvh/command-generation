from __future__ import annotations

import json
import tempfile
from pathlib import Path

from command_generation.primitive_executor import PrimitiveContext, execute_primitive, run_operation_steps


REQUIRED_PORTABLE_PRIMITIVES = {
    "path.target_root.resolve",
    "filesystem.read",
    "filesystem.glob",
    "json.parse",
    "payload.assemble",
    "output.emit",
}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package = root / "package"
        target = root / "target"
        package.mkdir()
        target.mkdir()
        (package / "items.json").write_text(json.dumps({"skills": [{"id": "demo", "path": "demo/SKILL.md"}]}), encoding="utf-8")
        (package / "file.txt").write_text("ok", encoding="utf-8")
        context = PrimitiveContext(cwd=root, roots={"package": package})

        assert execute_primitive("path.target_root.resolve", values={"target": "target"}, context=context)
        assert execute_primitive("filesystem.read", values={}, arguments={"root": "package", "path": "items.json"}, context=context)
        assert execute_primitive("filesystem.glob", values={}, arguments={"root": "package", "pattern": "**/*"}, context=context)
        assert execute_primitive("json.parse", values={"registry_text": "{}"}, context=context) == {}
        payload = execute_primitive(
            "payload.assemble",
            values={"registry": {"skills": [{"id": "demo", "path": "demo/SKILL.md"}]}},
            arguments={"fields": {"actions_from": "registry.skills"}},
            context=context,
        )
        assert payload["actions"]
        assert execute_primitive("output.emit", values={"result": payload, "format": "json"}, context=context)
        operation = {
            "ir_plan": {
                "steps": [
                    {
                        "uses": "filesystem.read",
                        "arguments": {"root": "package", "path": "items.json"},
                        "outputs": ["registry_text"],
                    },
                    {"uses": "json.parse", "outputs": ["registry"]},
                    {"uses": "payload.assemble", "arguments": {"fields": {"actions_from": "registry.skills"}}, "outputs": ["result"]},
                    {"uses": "output.emit", "outputs": ["emitted"]},
                ]
            }
        }
        assert "demo" in run_operation_steps(operation, initial_values={"format": "json"}, context=context)["emitted"]
    print("[ok] command-generation primitive conformance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
