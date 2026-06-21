# Projection primitives

`payload.project` is a host-neutral primitive for exact payload projection.

Command Generation owns only the mechanics:

- read a source value from the operation value map;
- split declared selector strings into exact dot paths;
- resolve object fields and list indexes;
- return a selected-output wrapper with `values`, `missing`, and `available_selectors`.

Host packages own the semantics:

- payload construction;
- selector names and command names;
- view policy, ordering, labels, and text;
- whether a missing selector is acceptable;
- any user-facing interpretation of the projected values.

The primitive intentionally does not evaluate expressions, execute embedded language snippets, infer selectors from prose, or encode host package vocabulary.
