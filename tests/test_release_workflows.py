from __future__ import annotations

import fnmatch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"


def _release_asset_patterns(workflow: str) -> list[str]:
    lines = workflow.splitlines()
    files_line = lines.index("          files: |")
    patterns: list[str] = []
    for line in lines[files_line + 1 :]:
        if not line.startswith("            "):
            break
        patterns.append(line.strip())
    return patterns


def _matching_release_assets(patterns: list[str], assets: list[str]) -> list[str]:
    return [
        asset
        for asset in assets
        if any(fnmatch.fnmatchcase(asset, pattern) for pattern in patterns)
    ]


def test_ci_builds_and_proves_install_from_package_artifact() -> None:
    workflow = (WORKFLOW_ROOT / "ci.yml").read_text(encoding="utf-8")

    assert "uv build" in workflow
    assert "python -m pip install dist/*.whl" in workflow
    assert "cd \"$(mktemp -d)\"" in workflow
    assert "import command_generation" in workflow
    assert "actions/upload-artifact" in workflow


def test_pr_semver_label_workflow_requires_label_for_package_changes() -> None:
    workflow = (WORKFLOW_ROOT / "pr-semver-label.yml").read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "labeled" in workflow
    assert "unlabeled" in workflow
    assert "semver:major" in workflow
    assert "semver:minor" in workflow
    assert "semver:patch" in workflow
    assert '".github/workflows/pr-semver-label.yml"' in workflow
    assert '".github/workflows/release-from-semver-label.yml"' in workflow
    assert '"pyproject.toml"' in workflow
    assert '"schemas/"' in workflow
    assert '"src/"' in workflow
    assert "must have exactly one" in workflow


def test_master_release_workflow_bumps_from_merged_pr_label() -> None:
    workflow = (WORKFLOW_ROOT / "release-from-semver-label.yml").read_text(
        encoding="utf-8"
    )

    assert "branches:" in workflow
    assert "master" in workflow
    assert "contents: write" in workflow
    assert "issues: read" in workflow
    assert "pull-requests: read" in workflow
    assert 'os.environ["GITHUB_ACTOR"] == "github-actions[bot]"' in workflow
    assert "Merge pull request #(\\d+)" in workflow
    assert "Direct push changed pyproject.toml; releasing explicit version" in workflow
    assert "Package-affecting direct push did not change pyproject.toml" in workflow
    assert 'output("release_needed", "false")' in workflow
    assert "set_release_outputs(current_version)" in workflow
    assert "parse_version(current_version)" in workflow
    assert "cat-file" in workflow
    assert 'f"{before}^{{commit}}"' in workflow
    assert "repos/{os.environ['REPOSITORY']}/issues/{pr_number}/labels" in workflow
    assert "semver:major" in workflow
    assert "semver:minor" in workflow
    assert "semver:patch" in workflow
    assert "uv lock" in workflow
    assert "uv run pytest" in workflow
    assert "uv run ruff check src tests" in workflow
    assert "uv build" in workflow
    assert "python -m pip install dist/*.whl" in workflow
    assert "sha256sum *.whl *.tar.gz > SHA256SUMS" in workflow
    assert "git commit -m \"Release ${{ steps.release-bump.outputs.tag }}\"" in workflow
    assert 'git tag "${{ steps.release-bump.outputs.tag }}"' in workflow
    assert "git diff --cached --quiet" in workflow
    assert "git rev-parse origin/master" in workflow
    assert 'git push origin "${{ steps.release-bump.outputs.tag }}"' in workflow
    assert "softprops/action-gh-release" in workflow
    assert "tag_name: ${{ steps.release-bump.outputs.tag }}" in workflow
    assert "dist/*.whl" in workflow
    assert "dist/*.tar.gz" in workflow
    assert "dist/SHA256SUMS" in workflow


def test_release_workflow_publishes_semver_tag_artifacts() -> None:
    workflow = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")

    assert '"v*.*.*"' in workflow
    assert "TAG_VERSION=\"${GITHUB_REF_NAME#v}\"" in workflow
    assert "Tag ${GITHUB_REF_NAME} does not match pyproject version" in workflow
    assert "uv build" in workflow
    assert "python -m pip install dist/*.whl" in workflow
    assert "softprops/action-gh-release" in workflow
    assert "sha256sum *.whl *.tar.gz > SHA256SUMS" in workflow
    assert "files: |" in workflow
    assert "dist/*.whl" in workflow
    assert "dist/*.tar.gz" in workflow
    assert "dist/SHA256SUMS" in workflow
    assert "generate_release_notes: true" in workflow


def test_release_asset_patterns_exclude_incidental_dist_files() -> None:
    workflow = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")

    patterns = _release_asset_patterns(workflow)

    assert _matching_release_assets(
        patterns,
        [
            "dist/command_generation-0.1.0-py3-none-any.whl",
            "dist/command_generation-0.1.0.tar.gz",
            "dist/SHA256SUMS",
            "dist/.gitignore",
            "dist/default.gitignore",
            "dist/command_generation-0.1.0-py3-none-any.whl.sha256",
            "dist/command_generation-0.1.0.intoto.jsonl",
        ],
    ) == [
        "dist/command_generation-0.1.0-py3-none-any.whl",
        "dist/command_generation-0.1.0.tar.gz",
        "dist/SHA256SUMS",
    ]


def test_release_notes_classify_compatibility_significant_changes() -> None:
    release_config = (ROOT / ".github" / "release.yml").read_text(encoding="utf-8")

    assert "Compatibility-significant changes" in release_config
    assert "schema" in release_config
    assert "generated-runtime" in release_config
    assert "conformance" in release_config


def test_workflows_use_node_24_action_generations() -> None:
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8") for path in WORKFLOW_ROOT.glob("*.yml")
    )

    assert "actions/checkout@v4" not in workflow_text
    assert "actions/setup-python@v5" not in workflow_text
    assert "astral-sh/setup-uv@v5" not in workflow_text
    assert "actions/checkout@v6.0.3" in workflow_text
    assert "actions/setup-python@v6.2.0" in workflow_text
    assert "astral-sh/setup-uv@v8.2.0" in workflow_text
