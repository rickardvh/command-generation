from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ci_builds_and_proves_install_from_package_artifact() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "uv build" in workflow
    assert "python -m pip install dist/*.whl" in workflow
    assert "cd \"$(mktemp -d)\"" in workflow
    assert "import command_generation" in workflow
    assert "actions/upload-artifact" in workflow


def test_release_workflow_publishes_semver_tag_artifacts() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert '"v*.*.*"' in workflow
    assert "TAG_VERSION=\"${GITHUB_REF_NAME#v}\"" in workflow
    assert "Tag ${GITHUB_REF_NAME} does not match pyproject version" in workflow
    assert "uv build" in workflow
    assert "python -m pip install dist/*.whl" in workflow
    assert "softprops/action-gh-release" in workflow
    assert "files: dist/*" in workflow
    assert "generate_release_notes: true" in workflow


def test_release_notes_classify_compatibility_significant_changes() -> None:
    release_config = (ROOT / ".github" / "release.yml").read_text(encoding="utf-8")

    assert "Compatibility-significant changes" in release_config
    assert "schema" in release_config
    assert "generated-runtime" in release_config
    assert "conformance" in release_config
