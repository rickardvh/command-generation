# Release And Versioning

`command-generation` is a maintainer dependency for host repositories that render command-package artifacts. It should be consumed as a versioned package artifact, not as a generated-runtime dependency.

## Release Goal

The ordinary downstream path should be:

1. CI builds wheel and sdist artifacts.
2. CI proves install-from-built-artifact.
3. A semver tag identifies the released package.
4. Host repositories pin a package version or compatible range.
5. Generated artifact metadata and host proof can report which generator version produced the outputs.

GitHub source installs are acceptable during development and transition, but they should not remain the ordinary compatibility signal.

## CI And Release Mechanics

Pull request CI builds the package with `uv build`, uploads the `dist/` artifacts, and installs the built wheel into a fresh virtual environment from outside the source tree. That install proof is the ordinary guard against accidentally relying on editable-source imports, untracked files, or repository layout.

Package-affecting PRs must have exactly one semver label: `semver:major`, `semver:minor`, or `semver:patch`. The semver label is the maintainer-owned compatibility decision for the release bump. Package-affecting paths include `src/`, `schemas/`, `pyproject.toml`, `uv.lock`, and release workflow files.

After a package-affecting PR merges to `master`, CI reads the merged PR label, bumps `project.version` in `pyproject.toml`, updates `uv.lock`, reruns tests and lint, rebuilds wheel/sdist artifacts, proves wheel installation from `dist/`, commits `Release vMAJOR.MINOR.PATCH`, pushes the matching tag, and attaches the artifacts to the GitHub Release.

Direct package-affecting pushes to `master` do not have PR labels to inspect. They may still publish a release when the push explicitly changes `project.version` in `pyproject.toml` to an unreleased `MAJOR.MINOR.PATCH` version. In that path CI uses the explicit version, refreshes `uv.lock`, proves the artifact, tags the existing commit, and publishes the GitHub Release.

Semver releases may also be cut by pushing a `vMAJOR.MINOR.PATCH` tag manually when the tag matches `project.version`.

Release notes are generated from merged PRs and classify compatibility-significant changes separately. PRs that change the command package IR schema, generated runtime layout, conformance semantics, target extension contract, or primitive behavior should use a compatibility label such as `schema`, `generated-runtime`, `conformance`, or `compatibility`.

## Compatibility Signals

The canonical command package IR schema version is `command-generation/command-package-ir/v1`. `load_command_package_ir(...)` accepts the former `agentic-workspace/command-package-ir/v1` value as a transitional compatibility alias and canonicalizes loaded manifests to the command-generation namespace. Changing the canonical schema namespace or removing an alias is compatibility-significant.

Release notes should call out changes that affect consumers:

- command package IR schema shape;
- generated Python or TypeScript artifact layout;
- generated artifact provenance metadata shape;
- generated callable or CLI adapter contracts;
- portable primitive behavior;
- conformance runner input or expected-output semantics;
- package-owned fixture case changes that consumers use as proof anchors.

Internal refactors that do not change these surfaces can stay patch-level changes. While the package is pre-1.0, compatibility-significant changes should still be explicit in release notes so consumers can choose safe pin ranges.

## Runtime Boundary

Generated runtimes must not import `command_generation`. They may contain rendered code, copied resources, and operation contracts emitted by this package, but runtime behavior should depend on the generated package and host-owned runtime modules.

This keeps the package as a build/proof dependency and lets host repositories reason about installed payload versions separately from generator versions.

## Consumer Responsibilities

Host repositories should:

- own product-specific operation contracts and runtime primitive implementations;
- declare which `command-generation` version produced generated artifacts;
- fail proof when generated artifacts are stale for the declared generator version;
- choose wrapper/process vs direct-function conformance based on the behavior under test.

Agentic Workspace is expected to consume this package by semver artifact once the release pipeline exists, while AW local-source dogfooding remains an AW repository concern.
