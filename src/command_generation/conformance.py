from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast


SelectedFields = Callable[[str], dict[str, object]]


@dataclass(frozen=True)
class ProcessConformanceCase:
    conformance_ref: str
    label: str
    success_args: tuple[str, ...]
    selected_fields: SelectedFields
    expected_fields: dict[str, object] | None
    stdout_contains: tuple[str, ...]
    fixture_id: str
    fixture_files: dict[str, str]
    expected_exit: int
    allow_stderr: bool


@dataclass(frozen=True)
class CliConformanceTarget:
    label: str
    command: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str] | None = None


@dataclass(frozen=True)
class CliConformanceFailure:
    target: str
    conformance_ref: str
    message: str


@dataclass(frozen=True)
class CliConformanceResult:
    target: str
    conformance_ref: str
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    selected_fields: dict[str, object] | None = None


def process_case_from_contract(
    *,
    contract: Mapping[str, object],
    command_placeholder: str,
    label: str | None = None,
) -> ProcessConformanceCase:
    """Project a process conformance contract into a target-independent case."""

    expectations = _mapping(contract.get("expectations", {}))
    stdout = _mapping(expectations.get("stdout", {}))
    assertions = _assertions(stdout.get("field_assertions", []), contract_id=str(contract.get("id", "")))
    stdout_contains = _strings(stdout.get("contains", []), contract_id=str(contract.get("id", "")), field_name="stdout.contains")
    fixture_id, fixture_files = _fixture_from_contract(contract)
    contract_id = str(contract.get("id", ""))
    return ProcessConformanceCase(
        conformance_ref=contract_id,
        label=label or contract_id.removesuffix(".process").replace(".", " "),
        success_args=tuple(_success_args_from_contract(contract=contract, command_placeholder=command_placeholder)),
        selected_fields=lambda stdout_text, contract_assertions=assertions: selected_contract_fields(
            stdout_text,
            contract_assertions,
        ),
        expected_fields=expected_contract_fields(assertions),
        stdout_contains=tuple(stdout_contains),
        fixture_id=fixture_id,
        fixture_files=fixture_files,
        expected_exit=_expected_exit_from_contract(contract),
        allow_stderr=_allow_stderr_from_contract(contract),
    )


def selected_contract_fields(stdout: str, assertions: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if not assertions:
        return {}
    payload = json.loads(stdout)
    selected: dict[str, object] = {}
    for assertion in assertions:
        path = assertion.get("path", [])
        if not isinstance(path, list) or not all(isinstance(part, str) for part in path):
            raise ValueError(f"conformance assertion path is malformed: {path!r}")
        field_path = [str(part) for part in path]
        selected[".".join(field_path)] = _field_value(payload, field_path)
    return selected


def expected_contract_fields(assertions: Sequence[Mapping[str, object]]) -> dict[str, object]:
    expected: dict[str, object] = {}
    for assertion in assertions:
        path = assertion.get("path", [])
        if not isinstance(path, list) or not all(isinstance(part, str) for part in path):
            raise ValueError(f"conformance assertion path is malformed: {path!r}")
        expected[".".join(str(part) for part in path)] = assertion.get("equals")
    return expected


def materialize_case_fixture(*, case: ProcessConformanceCase, root: Path) -> Path:
    fixture_root = root / case.fixture_id
    if fixture_root.exists():
        shutil.rmtree(fixture_root)
    fixture_root.mkdir(parents=True, exist_ok=True)
    for relative_path, contents in case.fixture_files.items():
        path = fixture_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    return fixture_root


def run_cli_conformance_case(
    *,
    case: ProcessConformanceCase,
    target: CliConformanceTarget,
    fixture_root: Path | None = None,
) -> tuple[CliConformanceResult | None, list[CliConformanceFailure]]:
    cwd = fixture_root or target.cwd
    command = (*target.command, *case.success_args)
    process = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=dict(target.env) if target.env is not None else None,
    )
    failures: list[CliConformanceFailure] = []
    selected: dict[str, object] | None = None
    if process.returncode != case.expected_exit:
        failures.append(
            CliConformanceFailure(
                target=target.label,
                conformance_ref=case.conformance_ref,
                message=(
                    f"{target.label} {case.label} exit code drifted from contract; "
                    f"expected {case.expected_exit}, got {process.returncode}; stderr={process.stderr!r}"
                ),
            )
        )
    if process.stderr.strip() and not case.allow_stderr:
        failures.append(
            CliConformanceFailure(
                target=target.label,
                conformance_ref=case.conformance_ref,
                message=f"{target.label} {case.label} emitted unexpected stderr: {process.stderr!r}",
            )
        )
    if case.expected_fields is not None and not failures:
        try:
            selected = case.selected_fields(process.stdout)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            failures.append(
                CliConformanceFailure(
                    target=target.label,
                    conformance_ref=case.conformance_ref,
                    message=(
                        f"{target.label} {case.label} stdout did not satisfy selected fields: {exc}; "
                        f"stdout={process.stdout!r}"
                    ),
                )
            )
        else:
            if selected != case.expected_fields:
                failures.append(
                    CliConformanceFailure(
                        target=target.label,
                        conformance_ref=case.conformance_ref,
                        message=(
                            f"{target.label} {case.label} output shape drifted; "
                            f"expected selected fields {case.expected_fields!r}, got {selected!r}"
                        ),
                    )
                )
    if case.stdout_contains and not failures:
        missing = [expected for expected in case.stdout_contains if expected not in process.stdout]
        if missing:
            failures.append(
                CliConformanceFailure(
                    target=target.label,
                    conformance_ref=case.conformance_ref,
                    message=(
                        f"{target.label} {case.label} stdout text drifted from contract; "
                        f"missing substrings {missing!r}; stdout={process.stdout!r}"
                    ),
                )
            )
    return (
        CliConformanceResult(
            target=target.label,
            conformance_ref=case.conformance_ref,
            command=command,
            returncode=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            selected_fields=selected,
        ),
        failures,
    )


def _success_args_from_contract(*, contract: Mapping[str, object], command_placeholder: str) -> list[str]:
    adapter = _mapping(contract.get("adapter", {}))
    template = adapter.get("command_template", [])
    if not isinstance(template, list) or not all(isinstance(token, str) for token in template):
        raise ValueError(f"conformance contract {contract.get('id')!r} has malformed command_template")
    tokens = [str(token) for token in template]
    expected_placeholder = "{" + command_placeholder + "}"
    if not tokens or tokens[0] != expected_placeholder:
        raise ValueError(
            f"conformance contract {contract.get('id')!r} starts with {tokens[0] if tokens else None!r}, "
            f"expected {expected_placeholder!r}"
        )
    return tokens[1:]


def _fixture_from_contract(contract: Mapping[str, object]) -> tuple[str, dict[str, str]]:
    fixtures = contract.get("fixtures", [])
    if not isinstance(fixtures, list) or not fixtures or not isinstance(fixtures[0], Mapping):
        raise ValueError(f"conformance contract {contract.get('id')!r} has no usable fixture")
    fixture = cast(Mapping[str, object], fixtures[0])
    fixture_id = fixture.get("id")
    files = fixture.get("files")
    if not isinstance(fixture_id, str) or not isinstance(files, Mapping) or not all(isinstance(key, str) for key in files):
        raise ValueError(f"conformance contract {contract.get('id')!r} fixture is malformed")
    fixture_files = cast(Mapping[str, object], files)
    return fixture_id, {path: str(contents) for path, contents in fixture_files.items()}


def _expected_exit_from_contract(contract: Mapping[str, object]) -> int:
    expectations = _mapping(contract.get("expectations", {}))
    exit_expectation = _mapping(expectations.get("exit", {}))
    code = exit_expectation.get("code", 0)
    return int(code) if isinstance(code, int) else 0


def _allow_stderr_from_contract(contract: Mapping[str, object]) -> bool:
    expectations = _mapping(contract.get("expectations", {}))
    stderr = _mapping(expectations.get("stderr", {}))
    return bool(stderr.get("allow_non_empty", False))


def _assertions(value: object, *, contract_id: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list) or not all(isinstance(assertion, Mapping) for assertion in value):
        raise ValueError(f"conformance contract {contract_id!r} has malformed field_assertions")
    return [cast(Mapping[str, object], assertion) for assertion in value]


def _strings(value: object, *, contract_id: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"conformance contract {contract_id!r} has malformed {field_name}")
    return [str(item) for item in value]


def _field_value(payload: object, path: list[str]) -> object:
    current = payload
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(".".join(path))
        current = cast(Mapping[str, object], current)[part]
    return current


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"expected mapping, got {type(value).__name__}")
    return cast(Mapping[str, object], value)
