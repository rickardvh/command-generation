from __future__ import annotations

import json
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def command_package_schema_path() -> Path:
    """Return the package-owned command-package IR schema path."""
    resource = files("command_generation.schemas").joinpath("command_package_ir.schema.json")
    with as_file(resource) as path:
        return Path(path)


def load_command_package_ir(ir_path: Path, schema_path: Path | None = None) -> dict[str, Any]:
    """Load and validate command-package IR from explicit paths."""
    effective_schema_path = schema_path or command_package_schema_path()
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    schema = json.loads(effective_schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(ir), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(error.message for error in errors)
        raise ValueError(f"{ir_path} does not match {effective_schema_path}: {details}")
    if not isinstance(ir, dict):
        raise ValueError(f"{ir_path} must contain a JSON object")
    return ir
