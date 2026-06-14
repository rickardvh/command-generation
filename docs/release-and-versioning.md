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

Semver releases are cut by pushing a `vMAJOR.MINOR.PATCH` tag. The release workflow validates that the tag version matches `project.version` in `pyproject.toml`, reruns tests and lint, rebuilds wheel/sdist artifacts, proves wheel installation from `dist/`, and attaches the artifacts to the GitHub Release.

Release notes are generated from merged PRs and classify compatibility-significant changes separately. PRs that change the command package IR schema, generated runtime layout, conformance semantics, target extension contract, or primitive behavior should use a compatibility label such as `schema`, `generated-runtime`, `conformance`, or `compatibility`.

## Compatibility Signals

Release notes should call out changes that affect consumers:

- command package IR schema shape;
- generated Python or TypeScript artifact layout;
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
