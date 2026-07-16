# Projection primitives

`payload.project` is a host-neutral primitive for exact payload projection.

Command Generation owns only the mechanics:

- read a source value from the operation value map;
- split declared selector strings into exact dot paths;
- resolve object fields and list indexes;
- return a selected-output wrapper with `values` only when every requested selector resolves;
- return a bounded selector-validation error when any selector is unknown.

Selector validation is atomic. A request with any unknown selector does not return
partial projected values. The validation error reports the requested selectors,
the unknown selectors, a small selector sample, the available selector count,
bounded suggestions, and discovery commands. It intentionally omits the complete
selector catalog from the error path.

Host packages own the semantics:

- payload construction;
- selector names and command names;
- view policy, ordering, labels, and text;
- the complete selector inventory/detail command;
- any user-facing interpretation of the projected values.

The primitive intentionally does not evaluate expressions, execute embedded language snippets, infer selectors from prose, or encode host package vocabulary.
