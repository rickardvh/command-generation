# Generated Target Layout Compatibility

Generated package resources carry `generation_metadata.target.layout_version` so hosts can tell whether generated artifacts match a layout they know how to inspect, package, and prove. The layout version is target-specific and separate from the command package IR schema version and the `command-generation` package version.

Current layout identifiers:

- Python: `command-generation/python-target-layout/v1`
- TypeScript: `command-generation/typescript-target-layout/v1`

## What The Layout Version Covers

A target layout version describes the generated artifact contract that hosts and proof tooling may observe:

- generated file and resource paths, including package resource locations;
- placement of `generation_metadata` and the target `layout_version`;
- runtime import and resource lookup paths emitted inside generated code;
- generated entrypoint, package metadata, `bin`, `files`, and test-resource layout for the target;
- target-scoped package resource shape, including target-specific runtime binding inclusion or exclusion.

Hosts may compare `generation_metadata.target.layout_version` against the set of layouts their proof and packaging logic supports. An unknown layout version should be treated as a compatibility signal: update the host proof/tooling or regenerate with a supported generator before trusting freshness or provenance.

## When To Change It

Change a target layout version when generated artifacts move or when host-observable lookup expectations change. Examples include:

- moving, renaming, adding, or removing generated files that hosts may package or prove;
- changing where `command_package.json` or `generation_metadata` is stored;
- changing generated runtime imports, package resource lookup paths, or entrypoint locations;
- changing TypeScript package metadata layout such as `files`, `bin`, or target-scoped resource placement;
- changing Python package resource layout or generated module paths used by imports.

Do not change a target layout version for implementation-only renderer refactors that preserve generated paths, metadata placement, import/resource lookup behavior, and package metadata expectations. Formatting, comments, and bug fixes that keep the same host-observable layout normally stay on the existing layout version.

## Release Notes

Layout-version changes are compatibility-significant. A PR that changes a target layout version should call out:

- the old and new layout identifiers;
- the generated paths or metadata placement that changed;
- the expected host action, such as updating proof support or regenerating artifacts.

This policy does not define downstream host packaging policy. Hosts own packaging decisions, but this package owns the generated layout identifiers and the metadata that lets hosts recognize them.
