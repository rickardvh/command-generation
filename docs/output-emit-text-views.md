# `output.emit` text views

`output.emit` accepts optional `text_views` arguments for host-neutral text rendering from JSON-shaped result payloads. Command Generation owns the rendering language and cross-target behavior. Host packages own view ids, labels, ordering, matching policy, and payload semantics.

## View Selection

`text_views` must be a list of objects. Each object may declare:

- `id`: optional view identifier for host documentation and review.
- `match`: object mapping dot paths to expected JSON scalar values.
- `default`: boolean marking the fallback view when `true`.
- `lines`: list of text line declarations.

Other view-level fields are rejected. `default` must be a boolean when present. Path-bearing and template-bearing line fields are strings: `literal`, `template`, `when`, `json`, `for_each.path`, and `for_each.template` do not accept arrays, objects, numbers, booleans, or null.

The first matching view renders. If no view matches, the last declared default view renders. If neither exists, `output.emit` falls back to its built-in compact text behavior.

`match` values are intentionally scalar-only: string, finite safe integer, boolean, or null. Arrays, objects, and non-integer or unsafe numeric values in `match` are rejected in every target. Actual result values are compared by explicit JSON scalar equality at exact dot paths, so booleans do not equal numbers.

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
- finite safe integers render without a trailing decimal.

Portable number rendering is intentionally limited to finite safe integers. Non-integer numbers, infinities, NaN, and integers outside JavaScript's safe integer range are rejected in placeholders, `join`, `match`, and JSON text-view blocks.

JSON blocks render with two-space indentation, recursively sorted object keys, and unescaped Unicode characters in Python and TypeScript generated runtimes. Sorting is lexicographic over string keys and is target-independent even for integer-index-like keys such as `"10"` and `"2"`.

## Failure Behavior

Malformed `text_views` fail at runtime with an `output.emit` error instead of silently falling back. Rejected cases include non-list `text_views`, non-object view entries, unsupported view fields, non-boolean `default` values, non-list `lines`, non-string path/template/literal line fields, unsupported filters, structured or unsafe-number `match` values, structured or unsafe-number direct placeholders, invalid `for_each` values, hidden invalid nested line declarations, and invalid `join` values.
