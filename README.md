# command-generation

`command-generation` renders command-package artifacts from a host-owned command package IR. It is a maintainer dependency: generated runtimes may contain the rendered outputs, but they do not import this package at runtime.

Public API:

- `load_command_package_ir(path, schema_path=None)` validates IR against the package-owned schema.
- `command_package_schema_path()` returns the packaged JSON schema.
- `render_outputs(manifest, repo_root, source_path, regenerate_command, host_manifest=None)` returns in-memory generated files.
- `generate_command_packages(..., check=True|False)` checks or writes generated files.
- `CommandGenerationHostManifest` declares host roots, custom primitive registry entries, target bindings, and optional host-owned runtime support.
- `PrimitiveRegistry` and `PrimitiveDefinition` describe portable or host-owned primitives with target support.

Hosts keep product-specific contracts, primitive implementations, and generated output ownership in their own repositories. The package owns generic rendering, schema loading, primitive registry validation, and portable primitive execution helpers.
