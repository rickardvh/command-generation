from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"[run] {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _latest_wheel(dist_dir: Path) -> Path:
    wheels = sorted(dist_dir.glob("command_generation-*.whl"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not wheels:
        raise SystemExit(f"no command-generation wheel found in {dist_dir}; run `uv build` first or pass --wheel")
    return wheels[0]


def _assert_artifact_import(*, python: Path, cg_root: Path, expected_version: str | None) -> None:
    script = """
import importlib.metadata
import json
from pathlib import Path
import command_generation

module_path = Path(command_generation.__file__).resolve()
cg_root = Path(__import__("os").environ["CG_SOURCE_ROOT"]).resolve()
payload = {
    "version": importlib.metadata.version("command-generation"),
    "module_path": str(module_path),
    "cg_root": str(cg_root),
}
try:
    module_path.relative_to(cg_root)
except ValueError:
    payload["source_tree_import"] = False
else:
    payload["source_tree_import"] = True
print(json.dumps(payload, indent=2))
if payload["source_tree_import"]:
    raise SystemExit("command_generation resolved to the command-generation source tree")
expected = __import__("os").environ.get("CG_EXPECTED_VERSION", "")
if expected and payload["version"] != expected:
    raise SystemExit(f"expected command-generation {expected}, got {payload['version']}")
"""
    env = os.environ.copy()
    env["CG_SOURCE_ROOT"] = str(cg_root)
    if expected_version:
        env["CG_EXPECTED_VERSION"] = expected_version
    _run([str(python), "-c", script], cwd=cg_root, env=env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prove AW consumes command-generation from a built artifact.")
    parser.add_argument("--aw-root", type=Path, default=REPO_ROOT.parent / "agentic-workspace")
    parser.add_argument("--wheel", type=Path, default=None)
    parser.add_argument("--dist-dir", type=Path, default=REPO_ROOT / "dist")
    parser.add_argument("--expected-version", default="")
    args = parser.parse_args(argv)

    aw_root = args.aw_root.resolve()
    if not (aw_root / "scripts" / "check" / "check_generated_command_packages.py").is_file():
        raise SystemExit(f"AW root does not look valid: {aw_root}")
    wheel = (args.wheel or _latest_wheel(args.dist_dir)).resolve()
    if not wheel.is_file():
        raise SystemExit(f"wheel does not exist: {wheel}")

    with tempfile.TemporaryDirectory(prefix="cg-aw-artifact-proof-") as tmp:
        venv = Path(tmp) / "venv"
        _run([sys.executable, "-m", "venv", str(venv)], cwd=REPO_ROOT)
        python = _venv_python(venv)
        _run([str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=REPO_ROOT)
        _run([str(python), "-m", "pip", "install", str(wheel)], cwd=REPO_ROOT)
        _assert_artifact_import(python=python, cg_root=REPO_ROOT, expected_version=args.expected_version or None)

        proof_commands = [
            [str(python), "scripts/generate/generate_command_packages.py", "--check"],
            [str(python), "scripts/check/check_generated_command_packages.py"],
            [str(python), "scripts/check/check_generated_command_packages.py", "--aw-primitive-ownership", "--format", "json"],
            [str(python), "scripts/check/run_operation_conformance_tests.py", "--target", "all"],
        ]
        proof_env = os.environ.copy()
        proof_env["PYTHONPATH"] = str(aw_root) + os.pathsep + proof_env.get("PYTHONPATH", "")
        for command in proof_commands:
            _run(command, cwd=aw_root, env=proof_env)

    print(f"[ok] AW consumed command-generation artifact {wheel.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
