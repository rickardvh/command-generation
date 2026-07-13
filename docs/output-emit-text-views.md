# `output.emit` text views

`output.emit` accepts optional `text_views` arguments for host-neutral text rendering from JSON-shaped result payloads. Command Generation owns the rendering language and cross-target behavior. Host packages own view ids, labels, ordering, matching policy, and payload semantics.

## View Selection

`text_views` must be a list of objects. Each object may declare:

- `id`: optional view identifier for host documentation and review.
- `match`: object mapping dot paths to expected JSON scalar values.
- `default`: truthy value marking the fallback view.
- `lines`: list of text line declarations.

The first matching view renders. If no view matches, the last declared default view renders. If neither exists, `output.emit` falls back to its built-in compact text behavior.

`match` values are intentionally scalar-only: string, number, boolean, or null. Arrays and objects in `match` are rejected in every target. Actual result values are compared by scalar equality at exact dot paths.

## Truthiness

Conditional lines use JSON-domain truthiness:

- `null`, missing values, empty strings, empty arrays, and empty objects are false.
- Non-empty strings, arrays, and objects are true.
- Booleans use their boolean value.
- Numbers use normal boolean truthiness, so `0` is false and other numbers are true.

## Line Forms

String lines are templates. Object lines use exactly one of these forms:

- `{"literal": "text"}` emits the literal text.
- `{"template": "text {path}"}` emits a template line.
- `{"when": "path", "lines": [...]}` emits nested lines only when the selected value is truthy.
- `{"for_each": {"path": "items", "lines": [...]}}` iterates over a list and renders nested lines with each item as the current value.
- `{"for_each": {"path": "items", "template": "- {}"}}` is shorthand for one template line per item.
- `{"json": "path"}` emits the selected value as an indented JSON block.

Missing `for_each` values, `null`, and empty strings render no lines. Present non-list `for_each` values are rejected.

## Placeholders And Filters

Templates replace `{path}` placeholders with scalar values. Empty `{}` and `{.}` refer to the current item. `root.` paths resolve against the root result payload.

Direct placeholders accept JSON scalars only. Arrays and objects must use the explicit `{"json": "path"}` line form. Missing values and null render as an empty string.

Supported filters:

- `len`: returns the length of a list; non-lists return `0`.
- `join:SEP`: joins a list of JSON scalar values with `SEP`.
- `empty:TEXT`: replaces falsey values with `TEXT`.

`join` treats missing and null values as empty so a later `empty` filter can provide fallback text. It rejects present non-list values and lists containing arrays or objects. It uses the same scalar formatter as direct placeholders.

Scalar formatting is portable:

- strings render as their raw string value;
- booleans render as `true` or `false`;
- null renders as an empty string;
- integer-valued numbers render without a trailing decimal.

JSON blocks render with two-space indentation, preserved object key order, and unescaped Unicode characters in Python and TypeScript generated runtimes.

## Failure Behavior

Malformed `text_views` fail at runtime with an `output.emit` error instead of silently falling back. Rejected cases include non-list `text_views`, non-object view entries, non-list `lines`, unsupported filters, structured `match` values, structured direct placeholders, invalid `for_each` values, and invalid `join` values.
