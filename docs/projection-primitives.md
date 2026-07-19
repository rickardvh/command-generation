# Projection primitives

`payload.project` is a host-neutral primitive for exact payload projection.

Command Generation owns only the mechanics:

- read a source value from the operation value map;
- split declared selector strings into exact dot paths;
- resolve object fields and list indexes;
- return a selected-output wrapper with `values` only when every requested selector resolves;
- reject selector requests with more than 32 selectors, any selector longer
  than 256 UTF-8 bytes, or more than 512 cumulative selector-name UTF-8 bytes
  before projection;
- return a bounded selector-validation error when any selector is unknown.

Selector validation is atomic. A request with any unknown selector does not return
partial projected values. The validation error reports the requested selectors,
the unknown selectors, a small selector sample, the available selector count,
bounded suggestions, and discovery commands. It intentionally omits the complete
selector catalog from the error path.

Selector request validation is also atomic. A request that exceeds the selector
count or UTF-8 byte budgets returns an `invalid-selector-request` error instead
of dropping, truncating, or mutating selectors. Validation-error payloads are
constructed to stay below the 6 KB upstream envelope: selector suggestions use
a fixed limit, selector samples and host command strings are budgeted, and
oversized host strings are omitted from the ordinary error envelope.

Host packages own the semantics:

- payload construction;
- selector names and command names;
- view policy, ordering, labels, and text;
- the exact selector inventory and detail commands, supplied as
  `selector_inventory_command` and `selector_detail_command` when validation
  errors need to point callers at discovery;
- any user-facing interpretation of the projected values.

The primitive intentionally does not evaluate expressions, execute embedded language snippets, infer selectors from prose, or encode host package vocabulary.
