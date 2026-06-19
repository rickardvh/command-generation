from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

from command_generation.host_manifest import CommandGenerationHostManifest
from command_generation.targets.contract import GeneratedOutput, _maturity_levels, _validate_target_primitive_support
from command_generation.targets.python import render_python_outputs
from command_generation.targets.typescript import render_typescript_outputs


TargetFamilyClassifier = Callable[[Path], str | None]


def generated_output_freshness_report(
    outputs: list[GeneratedOutput],
    *,
    repo_root: Path,
    required_target_families: list[str] | tuple[str, ...] = (),
    target_family_for_path: TargetFamilyClassifier | None = None,
) -> dict[str, Any]:
    """Summarize generated-output freshness without rewriting files.

    Hosts may provide target_family_for_path when their output layout has target
    families such as Python or TypeScript. The helper owns the generic compare,
    count, and digest mechanics; host repos own path classification semantics.
    """

    counts_by_family: dict[str, int] = {}
    stale_by_family: dict[str, list[str]] = {}
    digest_inputs_by_family: dict[str, list[str]] = {}
    for output in outputs:
        relative_path = output.path.relative_to(repo_root).as_posix()
        family = target_family_for_path(output.path) if target_family_for_path else None
        family_key = family or "unclassified"
        counts_by_family[family_key] = counts_by_family.get(family_key, 0) + 1
        digest_inputs_by_family.setdefault(family_key, []).append(f"{relative_path}\0{output.content}")
        current = output.path.read_text(encoding="utf-8") if output.path.is_file() else None
        if current != output.content:
            stale_by_family.setdefault(family_key, []).append(relative_path)

    digests_by_family: dict[str, str] = {}
    for family, digest_inputs in digest_inputs_by_family.items():
        digest = hashlib.sha256()
        for item in sorted(digest_inputs):
            digest.update(item.encode("utf-8"))
            digest.update(b"\0")
        digests_by_family[family] = digest.hexdigest()[:16]

    missing_families = [family for family in required_target_families if counts_by_family.get(family, 0) == 0]
    return {
        "status": "fresh" if not stale_by_family and not missing_families else "stale-or-incomplete",
        "rendered_output_count": len(outputs),
        "rendered_output_count_by_family": dict(sorted(counts_by_family.items())),
        "expected_digest_by_family": dict(sorted(digests_by_family.items())),
        "stale_output_count_by_family": {family: len(paths) for family, paths in sorted(stale_by_family.items())},
        "stale_outputs_by_family": {family: paths for family, paths in sorted(stale_by_family.items())},
        "required_target_families": list(required_target_families),
        "missing_target_families": missing_families,
        "cheap_check_rule": "Freshness checks compare rendered outputs in memory and do not rewrite generated files.",
    }


def render_outputs(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    source_path: str,
    regenerate_command: str,
    host_manifest: CommandGenerationHostManifest | dict[str, Any] | None = None,
) -> list[GeneratedOutput]:
    outputs: list[GeneratedOutput] = []
    host = CommandGenerationHostManifest.from_mapping(host_manifest, repo_root=repo_root)
    maturity_levels = _maturity_levels(manifest)
    runtime_binding = manifest["generation_policy"]["non_python_runtime_binding"]
    manifest_schema_version = str(manifest.get("schema_version", ""))
    for package in manifest["packages"]:
        for target in package["targets"]:
            _validate_target_primitive_support(package, target, repo_root=repo_root, host_manifest=host)
            root = repo_root / str(target["generated_root"])
            if target["kind"] == "python":
                outputs.extend(
                    render_python_outputs(
                        package,
                        target,
                        repo_root=repo_root,
                        root=root,
                        maturity_levels=maturity_levels,
                        manifest_schema_version=manifest_schema_version,
                        source_path=source_path,
                        regenerate_command=regenerate_command,
                        host_manifest=host,
                    )
                )
            elif target["kind"] == "typescript":
                outputs.extend(
                    render_typescript_outputs(
                        package,
                        target,
                        repo_root=repo_root,
                        root=root,
                        maturity_levels=maturity_levels,
                        runtime_binding=runtime_binding,
                        manifest_schema_version=manifest_schema_version,
                        source_path=source_path,
                        regenerate_command=regenerate_command,
                        host_manifest=host,
                    )
                )
    return outputs


def generate_command_packages(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    source_path: str,
    regenerate_command: str,
    check: bool,
    host_manifest: CommandGenerationHostManifest | dict[str, Any] | None = None,
) -> list[str]:
    stale_outputs: list[str] = []
    for output in render_outputs(
        manifest,
        repo_root=repo_root,
        source_path=source_path,
        regenerate_command=regenerate_command,
        host_manifest=host_manifest,
    ):
        if check:
            current = _read_generated_text(output.path) if output.path.exists() else ""
            if current != output.content:
                stale_outputs.append(output.path.relative_to(repo_root).as_posix())
        else:
            output.path.parent.mkdir(parents=True, exist_ok=True)
            output.path.write_text(output.content, encoding="utf-8", newline="\n")
            print(f"[ok] wrote {output.path.relative_to(repo_root).as_posix()}")
    return stale_outputs


def _read_generated_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()
