from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from command_generation.host_manifest import CommandGenerationHostManifest
from command_generation.targets.contract import (
    GeneratedOutput,
    TYPESCRIPT_TARGET_LAYOUT_VERSION,
    _command_operation_refs,
    _is_runnable_typescript_target,
    _json_block,
    generated_artifact_metadata,
    package_resource_with_generation_metadata,
    _python_adapter_commands,
    _python_resource_copies,
    _resource_copy_source_files,
    _typescript_minimal_operation,
    _version_fallback_for_package,
    _weak_agent_routing_for_target,
)


def _typescript_resource_copy_outputs(
    package: dict[str, Any],
    *,
    repo_root: Path,
    root: Path,
    host_manifest: CommandGenerationHostManifest,
) -> list[GeneratedOutput]:
    outputs: list[GeneratedOutput] = []
    if not _typescript_native_operation_ids(package):
        return outputs
    for copy in _python_resource_copies(package):
        source_root = repo_root / str(copy["source_root"])
        generated_root = root / "resources" / str(copy["generated_root"])
        required_marker = str(copy.get("required_marker") or "")
        if required_marker and not (source_root / required_marker).is_file():
            raise FileNotFoundError(
                f"missing required resource marker: {(source_root / required_marker).as_posix()}"
            )
        for source in _resource_copy_source_files(source_root):
            relative = source.relative_to(source_root)
            outputs.append(
                GeneratedOutput(
                    generated_root / relative, source.read_text(encoding="utf-8")
                )
            )

    operation_contract_root = repo_root / str(package["operation_contract_root"])
    native_ids = _typescript_native_operation_ids(package)
    emitted_operation_paths: set[str] = set()
    for command in _python_adapter_commands(package):
        for operation_ref in _command_operation_refs(command):
            operation_id = str(operation_ref.get("id", ""))
            operation_path = str(operation_ref.get("path", ""))
            if (
                operation_id not in native_ids
                or not operation_path
                or operation_path in emitted_operation_paths
            ):
                continue
            source = operation_contract_root / operation_path
            operation = (
                json.loads(source.read_text(encoding="utf-8"))
                if source.is_file()
                else _typescript_minimal_operation(
                    operation_id=operation_id,
                    schema_version=host_manifest.operation_schema_version,
                )
            )
            emitted_operation_paths.add(operation_path)
            outputs.append(
                GeneratedOutput(
                    root / "resources" / operation_path,
                    _json_block(
                        _typescript_executable_operation(
                            operation, operation_id=operation_id
                        )
                    )
                    + "\n",
                )
            )
    return outputs


def _typescript_native_operation_ids(package: dict[str, Any]) -> set[str]:
    operation_ids: set[str] = set()
    for command in _python_adapter_commands(package):
        for operation_ref in _command_operation_refs(command):
            operation_id = str(operation_ref.get("id", "")).strip()
            if operation_id:
                operation_ids.add(operation_id)
    return operation_ids


def _typescript_executable_operation(
    operation: dict[str, Any], *, operation_id: str
) -> dict[str, Any]:
    ir_plan = operation.get("ir_plan", {})
    steps = ir_plan.get("steps", []) if isinstance(ir_plan, dict) else []
    if isinstance(steps, list) and steps:
        return operation
    executable = dict(operation)
    executable["ir_plan"] = {
        "status": "complete",
        "summary": "Generated TypeScript native runtime binding for a command whose source operation has not yet been decomposed into portable IR.",
        "steps": [
            {
                "id": "execute_typescript_domain_operation",
                "uses": "typescript.domain.execute",
                "description": "Execute the operation through the generated TypeScript domain operation table.",
                "arguments": {"operation_id": operation_id},
                "outputs": ["result"],
                "on_error": "fail",
            },
            {
                "id": "emit_output",
                "uses": "output.emit",
                "description": "Emit the TypeScript-native operation result.",
                "arguments": {},
                "outputs": ["emitted"],
                "on_error": "emit_usage_error",
            },
        ],
    }
    return executable


def _typescript_package_json(
    package: dict[str, Any],
    target: dict[str, Any],
    maturity: dict[str, Any],
    runtime_binding: dict[str, Any],
    *,
    manifest_schema_version: str,
    source_path: str,
) -> str:
    payload = {
        "name": target["package_name"],
        "version": _version_fallback_for_package(package),
        "private": True,
        "type": "module",
        "files": ["src", "resources"],
        "bin": {entrypoint: "./src/cli.mjs" for entrypoint in target["entrypoints"]}
        if _is_runnable_typescript_target(target)
        else {},
        "scripts": {"test": "node --test test/command-package.test.mjs"},
        "agenticWorkspace": {
            "generated": True,
            "fixtureOnly": not _is_runnable_typescript_target(target),
            "generationStatus": target["generation_status"],
            "maturity": maturity,
            "runtimeBinding": {
                "selected_model": "generated parser, validation, and native TypeScript/Node command execution",
                "runtime_dependency": "node-only",
            },
            "generationMetadata": generated_artifact_metadata(
                manifest_schema_version=manifest_schema_version,
                target=target,
                target_layout_version=TYPESCRIPT_TARGET_LAYOUT_VERSION,
            ),
            "effectiveRuntimeCommand": None,
            "source": source_path,
            "program": package["program"],
            "declaredEntrypoints": target["entrypoints"],
        },
    }
    if not payload["bin"]:
        del payload["bin"]
    return _json_block(payload) + "\n"


def _typescript_module(
    package: dict[str, Any], *, source_path: str, regenerate_command: str
) -> str:
    return (
        "// Generated command package metadata.\n"
        f"// Source: {source_path}\n"
        f"// Program: {package['program']}\n"
        f"// Regenerate with: {regenerate_command}\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        "import { readFileSync } from 'node:fs';\n\n"
        "export type GeneratedCommandPackage = Record<string, unknown>;\n\n"
        "export const generatedCommandPackage = JSON.parse(\n"
        "  readFileSync(new URL('../resources/command_package.json', import.meta.url), 'utf8'),\n"
        ") as GeneratedCommandPackage;\n"
    )


def _typescript_interface_payload(package: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": str(command["command"]["name"]),
            "interface": command["interface"],
            "operation_ref": command.get("operation_ref", {}),
        }
        for command in package["commands"]
    ]


def _typescript_native_runtime_helpers(*, recovery_command: str) -> str:
    return (
        "function optionDefault(option) {\n"
        "  if (Object.prototype.hasOwnProperty.call(option, 'default')) return option.default;\n"
        "  if (option.action === 'store_true') return false;\n"
        "  if (option.action === 'append') return [];\n"
        "  if (option.nargs === '*') return [];\n"
        "  return undefined;\n"
        "}\n\n"
        "function initialValues(iface) {\n"
        "  const values = {};\n"
        "  for (const option of interfaceOptions(iface)) {\n"
        "    const optionName = option.name ?? optionFlags(option)[0];\n"
        "    if (!optionName) continue;\n"
        "    const defaultValue = optionDefault(option);\n"
        "    if (defaultValue !== undefined) values[optionName] = Array.isArray(defaultValue) ? [...defaultValue] : defaultValue;\n"
        "  }\n"
        "  return values;\n"
        "}\n\n"
        "function optionValue(option, token) {\n"
        "  const value = String(token);\n"
        "  return option.type === 'integer' ? Number(value) : value;\n"
        "}\n\n"
        "function argumentValue(argument, token) {\n"
        "  const value = String(token);\n"
        "  return argument.type === 'integer' ? Number(value) : value;\n"
        "}\n\n"
        "function parseInvocation(definition, tokens, path) {\n"
        "  const iface = definition.interface;\n"
        "  const values = initialValues(iface);\n"
        "  const positional = [];\n"
        "  let index = 0;\n"
        "  while (index < tokens.length) {\n"
        "    const token = String(tokens[index]);\n"
        "    if (isHelpToken(token)) {\n"
        "      printInterfaceHelp(path, iface);\n"
        "      process.exit(0);\n"
        "    }\n"
        "    if (token.startsWith('-')) {\n"
        "      const option = optionByFlag(iface, token);\n"
        "      if (!option) failValidation(`unknown option ${token} for ${path.join(' ')}`);\n"
        "      const optionName = option.name ?? optionFlags(option)[0];\n"
        "      if (option.action === 'store_true') {\n"
        "        values[optionName] = true;\n"
        "        index += 1;\n"
        "        continue;\n"
        "      }\n"
        "      if (option.action === 'append') {\n"
        "        if (index + 1 >= tokens.length || isHelpToken(tokens[index + 1])) failValidation(`${optionFlags(option)[0]} requires a value`);\n"
        "        if (!Array.isArray(values[optionName])) values[optionName] = [];\n"
        "        values[optionName].push(optionValue(option, tokens[index + 1]));\n"
        "        index += 2;\n"
        "        continue;\n"
        "      }\n"
        "      if (option.nargs === '*') {\n"
        "        const collected = [];\n"
        "        let cursor = index + 1;\n"
        "        while (cursor < tokens.length && !String(tokens[cursor]).startsWith('-')) {\n"
        "          collected.push(optionValue(option, tokens[cursor]));\n"
        "          cursor += 1;\n"
        "        }\n"
        "        values[optionName] = collected;\n"
        "        index = cursor;\n"
        "        continue;\n"
        "      }\n"
        "      values[optionName] = optionValue(option, tokens[index + 1]);\n"
        "      index += 2;\n"
        "      continue;\n"
        "    }\n"
        "    const subcommand = interfaceSubcommands(iface).find((candidate) => candidate.name === token);\n"
        "    if (subcommand) {\n"
        "      const nested = parseInvocation({ interface: subcommand, operation_ref: subcommand.operation_ref ?? definition.operation_ref }, tokens.slice(index + 1), [...path, token]);\n"
        "      if (iface.subcommand_dest) nested.values[iface.subcommand_dest] = token;\n"
        "      return nested;\n"
        "    }\n"
        "    positional.push(token);\n"
        "    index += 1;\n"
        "  }\n"
        "  interfaceArguments(iface).forEach((argument, position) => {\n"
        "    if (position < positional.length) values[argument.name] = argumentValue(argument, positional[position]);\n"
        "    else if (Object.prototype.hasOwnProperty.call(argument, 'default')) values[argument.name] = argument.default;\n"
        "  });\n"
        "  values._command_path = path;\n"
        "  return { values, operationRef: definition.operation_ref ?? iface.operation_ref ?? null };\n"
        "}\n\n"
        "function runNativeOperation(operationId, operationPath, values) {\n"
        "  if (!nativeOperationIds.has(operationId)) {\n"
        "    console.error(`Unsupported native TypeScript operation: ${operationId}`);\n"
        "    return 2;\n"
        "  }\n"
        "  return runGeneratedOperation({ operationId, operationPath, values });\n"
        "}\n\n"
        "function maybeRunNativeOperation() {\n"
        "  const invocation = parseInvocation(commandDefinitionByName.get(command), argv.slice(1), [command]);\n"
        "  const operationId = invocation.operationRef?.id;\n"
        "  const operationPath = invocation.operationRef?.path;\n"
        "  try {\n"
        "    const nativeStatus = runNativeOperation(operationId, operationPath, invocation.values);\n"
        "    process.exit(nativeStatus);\n"
        "  } catch (error) {\n"
        "    console.error(`TypeScript native runtime failed: ${error.message}`);\n"
        f"    console.error('Recovery: run {recovery_command} and inspect the generated command contract.');\n"
        "    process.exit(1);\n"
        "  }\n"
        "}\n\n"
    )


def _host_runtime_support_label(
    *, host_manifest: CommandGenerationHostManifest, support_path: Path
) -> str:
    if not support_path.is_absolute():
        return support_path.as_posix()
    if host_manifest.generated_root is None:
        return support_path.name
    try:
        return (
            support_path.resolve()
            .relative_to(host_manifest.generated_root.resolve().parent)
            .as_posix()
        )
    except ValueError:
        return support_path.name


def _typescript_runtime_module(
    *,
    source_path: str,
    regenerate_command: str,
    host_manifest: CommandGenerationHostManifest,
) -> str:
    support_import = ""
    configured_host_primitive_call = ""
    support_label = "none"
    if host_manifest.typescript_primitive_support_path is not None:
        support_label = _host_runtime_support_label(
            host_manifest=host_manifest,
            support_path=host_manifest.typescript_primitive_support_path,
        )
        support_import = "import { executeHostPrimitive as configuredHostPrimitive } from './hostPrimitiveSupport.mjs';\n"
        configured_host_primitive_call = "  if (typeof configuredHostPrimitive === 'function') return configuredHostPrimitive(primitive, values, args, operationId);\n"
    return f"""// Generated native TypeScript operation runtime.
// Source: {source_path}
// Host primitive support: {support_label}
// Regenerate with: {regenerate_command}
// DO NOT EDIT DIRECTLY.

import {{ existsSync, readFileSync, readdirSync, statSync, writeSync }} from 'node:fs';
import {{ dirname, isAbsolute, join, relative, resolve }} from 'node:path';
import {{ fileURLToPath }} from 'node:url';
{support_import}

const resourcesRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../resources');

class RuntimeError extends Error {{}}

function isObject(value) {{
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}}

function readText(path) {{
  return readFileSync(path, 'utf8');
}}

function readJson(path) {{
  return JSON.parse(readText(path));
}}

function resolveInside(root, subpath) {{
  const rootPath = resolve(root);
  const candidate = resolve(rootPath, String(subpath ?? ''));
  const rel = relative(rootPath, candidate);
  if (rel === '' || (!rel.startsWith('..') && !isAbsolute(rel))) return candidate;
  throw new RuntimeError(`path escapes primitive root: ${{candidate}}`);
}}

function resourceRoot(name) {{
  if (!name) return resourcesRoot;
  if (name.endsWith('.contracts') || name === '_contracts') return resolveInside(resourcesRoot, '_contracts');
  if (name.endsWith('.payload') || name.endsWith('.package-payload') || name === '_payload') return resolveInside(resourcesRoot, '_payload');
  if (name.endsWith('.skills') || name.endsWith('.package-skills') || name === '_skills') return resolveInside(resourcesRoot, '_skills');
  return resolveInside(resourcesRoot, name);
}}

function valueRoot(args, values) {{
  if (Object.prototype.hasOwnProperty.call(args, 'base_value')) {{
    const key = String(args.base_value);
    if (!Object.prototype.hasOwnProperty.call(values, key)) throw new RuntimeError(`unknown primitive base value: ${{key}}`);
    return resolve(String(values[key]));
  }}
  return resourceRoot(String(args.root ?? ''));
}}

function listFiles(root, prefix = '') {{
  const dir = resolveInside(root, prefix);
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir, {{ withFileTypes: true }})) {{
    const child = join(prefix, entry.name);
    if (entry.isDirectory()) out.push(...listFiles(root, child));
    else if (entry.isFile()) out.push(child.replace(/\\\\/g, '/'));
  }}
  return out.sort();
}}

function globFiles(root, pattern) {{
  if (!pattern || isAbsolute(pattern) || pattern.split(/[\\/]+/).includes('..')) throw new RuntimeError(`unsupported filesystem.glob pattern: ${{pattern}}`);
  const normalized = String(pattern).replace(/\\\\/g, '/');
  const files = listFiles(root);
  if (normalized === '**/*') return files;
  if (normalized.endsWith('/**/*')) {{
    const prefix = normalized.slice(0, -4);
    return files.filter((file) => file.startsWith(prefix));
  }}
  if (normalized.startsWith('**/*.')) {{
    const suffix = normalized.slice(4);
    return files.filter((file) => file.endsWith(suffix));
  }}
  if (!normalized.includes('*')) return files.filter((file) => file === normalized);
  const escaped = normalized.replace(/[.+^${{}}()|[\\]\\\\]/g, '\\\\$&').replace(/\\*\\*/g, '.*').replace(/\\*/g, '[^/]*');
  const regex = new RegExp(`^${{escaped}}$`);
  return files.filter((file) => regex.test(file));
}}

function conditionMatches(condition, values) {{
  if (condition === undefined || condition === null || (isObject(condition) && Object.keys(condition).length === 0)) return true;
  if (!isObject(condition)) throw new RuntimeError('step when condition must be an object');
  const keys = Object.keys(condition);
  if (keys.length === 1 && keys[0] === 'all') return condition.all.every((item) => conditionMatches(item, values));
  if (keys.length === 1 && keys[0] === 'any') return condition.any.some((item) => conditionMatches(item, values));
  if (keys.length === 1 && keys[0] === 'not') return !conditionMatches(condition.not, values);
  const actual = values[String(condition.value ?? '')];
  if (Object.prototype.hasOwnProperty.call(condition, 'equals')) return actual === condition.equals;
  if (Object.prototype.hasOwnProperty.call(condition, 'present')) return (actual !== undefined && actual !== null) === Boolean(condition.present);
  throw new RuntimeError('step when condition must use all, any, not, equals, or present');
}}

function storeStepResult(values, outputs, result) {{
  if (result === undefined || result === null) return;
  const names = Array.isArray(outputs) ? outputs.map(String).filter(Boolean) : [];
  if (names.length === 0) values._last = result;
  else if (names.length === 1) values[names[0]] = result;
  else {{
    if (!isObject(result)) throw new RuntimeError('multi-output primitive results must be objects');
    for (const name of names) {{
      if (!Object.prototype.hasOwnProperty.call(result, name)) throw new RuntimeError(`primitive result missing declared output: ${{name}}`);
      values[name] = result[name];
    }}
  }}
}}

function resolveTemplate(template, values) {{
  if (Array.isArray(template)) return template.map((item) => resolveTemplate(item, values));
  if (!isObject(template)) return template;
  const keys = Object.keys(template);
  if (keys.length === 1 && keys[0] === '$value') return values[String(template.$value)];
  if (keys.length === 1 && keys[0] === '$count') return Array.isArray(values[String(template.$count)]) ? values[String(template.$count)].length : 0;
  if (keys.length === 1 && keys[0] === '$select_by_value') {{
    const spec = template.$select_by_value;
    if (!isObject(spec) || !isObject(spec.choices)) throw new RuntimeError('template $select_by_value choices must be an object');
    let selectedKey = String(values[String(spec.value ?? '')] ?? spec.default ?? '');
    if (!Object.prototype.hasOwnProperty.call(spec.choices, selectedKey)) selectedKey = String(spec.default ?? '');
    if (!Object.prototype.hasOwnProperty.call(spec.choices, selectedKey)) throw new RuntimeError(`template $select_by_value cannot resolve choice for ${{String(spec.value ?? '')}}`);
    return resolveTemplate(spec.choices[selectedKey], values);
  }}
  return Object.fromEntries(Object.entries(template).map(([key, value]) => [key, resolveTemplate(value, values)]));
}}

function dottedValue(root, dottedPath) {{
  if (!dottedPath) return null;
  let current = root;
  for (const part of String(dottedPath).split('.')) {{
    if (!isObject(current) || !Object.prototype.hasOwnProperty.call(current, part)) return null;
    current = current[part];
  }}
  return current;
}}

function fieldByPath(root, dottedPath) {{
  if (!dottedPath) return [false, null];
  let current = root;
  for (const part of String(dottedPath).split('.')) {{
    if (isObject(current) && Object.prototype.hasOwnProperty.call(current, part)) {{
      current = current[part];
      continue;
    }}
    if (Array.isArray(current)) {{
      const index = Number(part);
      if (Number.isInteger(index) && index >= 0 && index < current.length) {{
        current = current[index];
        continue;
      }}
    }}
    return [false, null];
  }}
  return [true, current];
}}

const MAX_PROJECTION_SELECTORS = 32;
const MAX_PROJECTION_SELECTOR_LENGTH = 256;
const SELECTOR_INVENTORY_SAMPLE_LIMIT = 8;
const SELECTOR_SUGGESTION_LIMIT = 3;

function selectorLimitError(reason, requestedSelectorCount, selectorIndex = null, selectorLength = null) {{
  const error = {{
    reason,
    requested_selector_count: requestedSelectorCount,
    max_selectors: MAX_PROJECTION_SELECTORS,
    max_selector_length: MAX_PROJECTION_SELECTOR_LENGTH
  }};
  if (selectorIndex !== null) error.selector_index = selectorIndex;
  if (selectorLength !== null) error.selector_length = selectorLength;
  return error;
}}

function selectorTokensFromArray(value) {{
  const selectors = [];
  let requestedSelectorCount = 0;
  for (const item of value) {{
    const token = String(item).trim();
    if (!token) continue;
    requestedSelectorCount += 1;
    if (requestedSelectorCount > MAX_PROJECTION_SELECTORS) {{
      return {{ selectors, error: selectorLimitError('too-many-selectors', requestedSelectorCount, requestedSelectorCount - 1) }};
    }}
    if (token.length > MAX_PROJECTION_SELECTOR_LENGTH) {{
      return {{ selectors, error: selectorLimitError('selector-too-long', requestedSelectorCount, requestedSelectorCount - 1, token.length) }};
    }}
    selectors.push(token);
  }}
  return {{ selectors, error: null }};
}}

function selectorTokensFromString(value) {{
  const selectors = [];
  let requestedSelectorCount = 0;
  let token = '';
  let pendingWhitespace = 0;
  let seenNonWhitespace = false;
  function appendSelector() {{
    if (!token) return null;
    requestedSelectorCount += 1;
    if (requestedSelectorCount > MAX_PROJECTION_SELECTORS) {{
      token = '';
      pendingWhitespace = 0;
      return selectorLimitError('too-many-selectors', requestedSelectorCount, requestedSelectorCount - 1);
    }}
    selectors.push(token);
    token = '';
    pendingWhitespace = 0;
    return null;
  }}
  for (const char of String(value ?? '')) {{
    if (char === ',') {{
      const error = appendSelector();
      if (error) return {{ selectors, error }};
      seenNonWhitespace = false;
      continue;
    }}
    if (/\\s/u.test(char) && !seenNonWhitespace) continue;
    if (/\\s/u.test(char)) {{
      pendingWhitespace += 1;
      continue;
    }}
    if (pendingWhitespace) {{
      token += ' '.repeat(pendingWhitespace);
      pendingWhitespace = 0;
    }}
    seenNonWhitespace = true;
    token += char;
    if (token.length > MAX_PROJECTION_SELECTOR_LENGTH) {{
      requestedSelectorCount += 1;
      return {{
        selectors,
        error: selectorLimitError('selector-too-long', requestedSelectorCount, requestedSelectorCount - 1, token.length)
      }};
    }}
  }}
  return {{ selectors, error: appendSelector() }};
}}

function selectorTokens(value) {{
  if (Array.isArray(value)) return selectorTokensFromArray(value);
  return selectorTokensFromString(value);
}}

function selectorInventorySummary(payload, sampleLimit = 8) {{
  let count = 0;
  const sample = [];
  function recordSample(path) {{
    if (sampleLimit <= 0) return;
    sample.push(path);
    sample.sort();
    if (sample.length > sampleLimit) sample.pop();
  }}
  function visit(current, prefix) {{
    if (Array.isArray(current)) {{
      for (let index = 0; index < current.length; index += 1) {{
        const path = prefix ? `${{prefix}}.${{index}}` : String(index);
        count += 1;
        recordSample(path);
        visit(current[index], path);
      }}
      return;
    }}
    if (isObject(current)) {{
      for (const key in current) {{
        if (!Object.prototype.hasOwnProperty.call(current, key)) continue;
        const path = prefix ? `${{prefix}}.${{key}}` : key;
        count += 1;
        recordSample(path);
        visit(current[key], path);
      }}
    }}
  }}
  visit(payload, '');
  return {{ count, sample }};
}}

function selectorValidationKind(selectedOutputKind) {{
  const kind = String(selectedOutputKind ?? '');
  if (kind.includes('/selected-output/')) return kind.replace('/selected-output/', '/selector-validation-error/');
  if (kind.endsWith('/selected-output')) return `${{kind.slice(0, -'/selected-output'.length)}}/selector-validation-error`;
  return 'command-generation/selector-validation-error/v1';
}}

function selectorSuggestions(unknown, available, limit = 3) {{
  const terms = String(unknown).replaceAll('_', '.').split('.').filter(Boolean);
  const matches = [];
  for (const selector of available) {{
    const selectorTerms = String(selector).split('.');
    if (String(selector).includes(String(unknown)) || terms.some((term) => selectorTerms.includes(term) || String(selector).includes(term))) {{
      matches.push(selector);
    }}
    if (matches.length >= limit) return matches;
  }}
  return available.slice(0, limit);
}}

function selectorValidationError(payload, selectors, missing, sourceCommand, selectedOutputKind, discoveryCommand, detailCommand) {{
  const sampleLimit = SELECTOR_INVENTORY_SAMPLE_LIMIT;
  const {{ count, sample: available }} = selectorInventorySummary(payload, sampleLimit);
  const suggestions = {{}};
  for (const selector of missing) suggestions[selector] = selectorSuggestions(selector, available, SELECTOR_SUGGESTION_LIMIT);
  return {{
    kind: selectorValidationKind(selectedOutputKind),
    status: 'invalid-selector',
    source_command: sourceCommand,
    requested_selectors: selectors,
    unknown_selectors: missing,
    selector_inventory: {{
      status: 'omitted-from-validation-error',
      available_count: count,
      sample: available,
      sample_limit: sampleLimit,
      discovery_command: discoveryCommand,
      inventory_command: detailCommand,
      rule: 'Full selector inventories are omitted from validation errors; use the inventory command for complete details.'
    }},
    suggestions,
    validation_rule: 'Selector requests are atomic: any unknown selector prevents partial projection output.'
  }};
}}

function selectorRequestValidationError(selectors, requestError, sourceCommand, selectedOutputKind) {{
  return {{
    kind: selectorValidationKind(selectedOutputKind),
    status: 'invalid-selector-request',
    source_command: sourceCommand,
    requested_selectors: selectors,
    selector_request: {{ status: 'rejected', ...requestError }},
    validation_rule: 'Selector requests are bounded and atomic: too many selectors or overlong selectors are rejected before projection.'
  }};
}}

function projectPayload(values, args) {{
  const sourceName = String(args.source ?? 'result');
  if (!Object.prototype.hasOwnProperty.call(values, sourceName)) throw new RuntimeError(`payload.project source value is missing: ${{sourceName}}`);
  const payload = values[sourceName];
  const selectValueName = String(args.select_value ?? 'select');
  const selectedOutputKind = String(args.selected_output_kind ?? 'command-generation/selected-output/v1');
  const sourceCommand = String(args.source_command ?? values.operation_id ?? '');
  const selectorRequest = selectorTokens(args.selectors ?? values[selectValueName]);
  const selectors = selectorRequest.selectors;
  if (selectorRequest.error) return selectorRequestValidationError(selectors, selectorRequest.error, sourceCommand, selectedOutputKind);
  if (selectors.length === 0) return payload;
  const discoveryCommand = String(args.selector_inventory_command ?? '');
  const detailCommand = String(args.selector_detail_command ?? '');
  const missing = selectors.filter((selector) => !fieldByPath(payload, selector)[0]);
  if (missing.length) return selectorValidationError(payload, selectors, missing, sourceCommand, selectedOutputKind, discoveryCommand, detailCommand);
  const selected = {{ kind: selectedOutputKind, source_command: sourceCommand, values: {{}} }};
  for (const selector of selectors) {{
    const [found, value] = fieldByPath(payload, selector);
    if (found) selected.values[selector] = value;
    else missing.push(selector);
  }}
  return selected;
}}

function assemblePayload(values, args) {{
  const fields = args.fields ?? {{}};
  if (fields.template !== undefined) return resolveTemplate(fields.template, values);
  if (fields.payload_kind === 'package-file-list') {{
    const filesFrom = String(fields.files_from ?? 'files');
    const bundledSkillsFrom = String(fields.bundled_skill_files_from ?? 'bundled_skill_files');
    return {{
      files: relativePathList(values[filesFrom] ?? [], filesFrom),
      default_files: stringList(fields.default_files ?? [], 'payload.assemble fields.default_files'),
      optional_files: stringList(fields.optional_files ?? [], 'payload.assemble fields.optional_files'),
      bundled_skill_files: relativePathList(values[bundledSkillsFrom] ?? [], bundledSkillsFrom),
      optional_enable_commands: stringList(fields.optional_enable_commands ?? [], 'payload.assemble fields.optional_enable_commands')
    }};
  }}
  if (fields.payload_kind === 'package-resource-manifest') {{
    const manifestFrom = String(fields.manifest_from ?? 'manifest');
    const manifest = values[manifestFrom] ?? {{}};
    if (!isObject(manifest)) throw new RuntimeError(`${{manifestFrom}} must be an object`);
    const filesPath = String(fields.files_path ?? 'files');
    const bundledSkillsPath = String(fields.bundled_skill_files_path ?? 'bundled_skill_files');
    return {{
      files: manifestPathList(dottedValue(manifest, filesPath) ?? [], `${{manifestFrom}}.${{filesPath}}`),
      default_files: stringList(fields.default_files ?? [], 'payload.assemble fields.default_files'),
      optional_files: stringList(fields.optional_files ?? [], 'payload.assemble fields.optional_files'),
      bundled_skill_files: manifestPathList(dottedValue(manifest, bundledSkillsPath) ?? [], `${{manifestFrom}}.${{bundledSkillsPath}}`),
      optional_enable_commands: stringList(fields.optional_enable_commands ?? [], 'payload.assemble fields.optional_enable_commands')
    }};
  }}
  const payload = {{ dry_run: Boolean(fields.dry_run ?? true), message: String(fields.message ?? '') }};
  if (values.target_root !== undefined) payload.target_root = String(values.target_root);
  if (fields.actions_from === 'files') {{
    payload.actions = (values.files ?? []).map((item) => ({{ kind: 'file', path: String(item.relative_path ?? '') }}));
    return payload;
  }}
  if (fields.actions_from === 'registry.skills') {{
    payload.mode = String(fields.mode ?? 'skills');
    payload.bootstrap_version = dottedValue(values.registry ?? {{}}, String(fields.bootstrap_version_from ?? ''));
    payload.actions = (values.registry?.skills ?? []).filter(isObject).map((item) => ({{ kind: 'skill', id: String(item.id ?? ''), path: String(item.path ?? '') }}));
    return payload;
  }}
  throw new RuntimeError(`unsupported payload.assemble actions_from: ${{fields.actions_from}}`);
}}

function stringList(value, source) {{
  if (!Array.isArray(value) || !value.every((item) => typeof item === 'string')) throw new RuntimeError(`${{source}} must be a list of strings`);
  return value;
}}

function relativePathList(value, source) {{
  if (!Array.isArray(value)) throw new RuntimeError(`${{source}} must be a list`);
  return value.map((item) => {{
    if (typeof item === 'string') return item;
    if (isObject(item) && typeof item.relative_path === 'string') return item.relative_path;
    throw new RuntimeError(`${{source}} entries must be strings or objects with relative_path`);
  }});
}}

function manifestPathList(value, source) {{
  if (!Array.isArray(value)) throw new RuntimeError(`${{source}} must be a list`);
  return value.map((item) => {{
    if (typeof item === 'string') return item;
    if (isObject(item) && typeof item.relative_path === 'string') return item.relative_path;
    if (isObject(item) && typeof item.path === 'string') return item.path;
    throw new RuntimeError(`${{source}} entries must be strings or objects with path`);
  }});
}}

function emitOutput(values, args = {{}}) {{
  const result = values.result;
  if (String(values.format ?? 'text') === 'json') return `${{JSON.stringify(result, null, 2)}}\n`;
  if (isObject(result)) {{
    const declaredView = emitDeclaredTextView(result, args.text_views ?? []);
    if (declaredView !== null) return declaredView;
  }}
  if (!isObject(result)) return `${{result}}\n`;
  if (Array.isArray(result.files) && result.files.every((item) => typeof item === 'string')) return `${{result.files.join('\\n')}}\n`;
  const lines = [String(result.message ?? result.kind ?? '')];
  for (const action of (Array.isArray(result.actions) ? result.actions : [])) lines.push(`- ${{action.path ?? action.id ?? action.kind}}`);
  return `${{lines.join('\\n').trimEnd()}}\n`;
}}

function emitDeclaredTextView(result, views) {{
  if (views === null || views === undefined) return null;
  if (!Array.isArray(views)) throw new RuntimeError('output.emit text_views must be a list');
  for (const view of views) {{
    if (!isObject(view)) throw new RuntimeError('output.emit text_views entries must be objects');
    validateDeclaredTextView(view);
  }}
  let defaultView = null;
  for (const view of views) {{
    if (view.default === true) defaultView = view;
    if (declaredTextViewMatches(result, view)) return renderDeclaredTextView(result, view);
  }}
  return defaultView ? renderDeclaredTextView(result, defaultView) : null;
}}

function declaredTextViewMatches(result, view) {{
  const match = view.match ?? {{}};
  if (!isObject(match) || Object.keys(match).length === 0) return false;
  for (const [path, expected] of Object.entries(match)) {{
    if (!declaredTextIsScalar(expected)) throw new RuntimeError('output.emit text view match values must be JSON scalars');
    const [found, actual] = fieldByPath(result, path);
    if (!found || !declaredTextScalarEqual(actual, expected)) return false;
  }}
  return true;
}}

function validateDeclaredTextView(view) {{
  const allowedViewKeys = new Set(['id', 'match', 'default', 'lines']);
  if (Object.keys(view).some((key) => !allowedViewKeys.has(key))) throw new RuntimeError('output.emit text view has unsupported fields');
  if (Object.prototype.hasOwnProperty.call(view, 'default') && typeof view.default !== 'boolean') throw new RuntimeError('output.emit text view default must be a boolean');
  const match = view.match ?? {{}};
  if (Object.prototype.hasOwnProperty.call(view, 'match') && !isObject(match)) throw new RuntimeError('output.emit text view match must be an object');
  for (const expected of Object.values(match)) {{
    if (!declaredTextIsScalar(expected)) throw new RuntimeError('output.emit text view match values must be JSON scalars');
  }}
  if (Object.prototype.hasOwnProperty.call(view, 'lines')) validateDeclaredTextLines(view.lines);
}}

function validateDeclaredTextLines(lines) {{
  if (!Array.isArray(lines)) throw new RuntimeError('output.emit text view lines must be a list');
  for (const line of lines) validateDeclaredTextLine(line);
}}

function validateDeclaredTextLine(line) {{
  if (typeof line === 'string') return;
  if (!isObject(line)) throw new RuntimeError('output.emit text view lines must be strings or objects');
  const discriminators = ['when', 'for_each', 'json', 'template', 'literal'];
  const present = discriminators.filter((key) => Object.prototype.hasOwnProperty.call(line, key));
  if (present.length !== 1) throw new RuntimeError('output.emit text view line object must declare exactly one of when, for_each, json, template, or literal');
  const key = present[0];
  const keys = Object.keys(line).sort();
  if (key === 'literal') {{
    if (keys.length !== 1 || keys[0] !== 'literal') throw new RuntimeError('output.emit literal line must only declare literal');
    requireDeclaredTextString(line.literal, 'output.emit literal line value must be a string');
    return;
  }}
  if (key === 'template') {{
    if (keys.length !== 1 || keys[0] !== 'template') throw new RuntimeError('output.emit template line must only declare template');
    requireDeclaredTextString(line.template, 'output.emit template line value must be a string');
    return;
  }}
  if (key === 'json') {{
    if (keys.length !== 1 || keys[0] !== 'json') throw new RuntimeError('output.emit json line must only declare json');
    requireDeclaredTextString(line.json, 'output.emit json line path must be a string');
    return;
  }}
  if (key === 'when') {{
    if (keys.length !== 2 || keys[0] !== 'lines' || keys[1] !== 'when') throw new RuntimeError('output.emit when line must declare when and lines');
    requireDeclaredTextString(line.when, 'output.emit when line path must be a string');
    validateDeclaredTextLines(line.lines);
    return;
  }}
  const spec = line.for_each;
  if (!isObject(spec)) throw new RuntimeError('output.emit for_each line must be an object');
  if (!Object.prototype.hasOwnProperty.call(spec, 'path')) throw new RuntimeError('output.emit for_each line must declare path');
  requireDeclaredTextString(spec.path, 'output.emit for_each path must be a string');
  const nestedForms = ['lines', 'template'].filter((name) => Object.prototype.hasOwnProperty.call(spec, name));
  if (nestedForms.length !== 1) throw new RuntimeError('output.emit for_each line must declare exactly one of lines or template');
  const specKeys = Object.keys(spec).sort();
  const expectedKeys = ['path', nestedForms[0]].sort();
  if (specKeys.length !== 2 || specKeys[0] !== expectedKeys[0] || specKeys[1] !== expectedKeys[1]) throw new RuntimeError('output.emit for_each line has unsupported fields');
  if (Object.prototype.hasOwnProperty.call(spec, 'lines')) validateDeclaredTextLines(spec.lines);
  else requireDeclaredTextString(spec.template, 'output.emit for_each template must be a string');
}}

function requireDeclaredTextString(value, message) {{
  if (typeof value !== 'string') throw new RuntimeError(message);
}}

function renderDeclaredTextView(result, view) {{
  return `${{renderDeclaredTextLines(view.lines ?? [], result, result).join('\\n').trimEnd()}}\n`;
}}

function renderDeclaredTextLines(lines, current, root) {{
  if (!Array.isArray(lines)) throw new RuntimeError('output.emit text view lines must be a list');
  return lines.flatMap((line) => renderDeclaredTextLine(line, current, root));
}}

function renderDeclaredTextLine(line, current, root) {{
  if (typeof line === 'string') return [renderDeclaredTextTemplate(line, current, root)];
  if (!isObject(line)) throw new RuntimeError('output.emit text view lines must be strings or objects');
  if (Object.prototype.hasOwnProperty.call(line, 'when')) {{
    const [found, value] = declaredTextValue(line.when, current, root);
    return found && declaredTextTruthy(value) ? renderDeclaredTextLines(line.lines ?? [], current, root) : [];
  }}
  if (Object.prototype.hasOwnProperty.call(line, 'for_each')) {{
    const spec = line.for_each;
    if (!isObject(spec)) throw new RuntimeError('output.emit for_each line must be an object');
    const [found, value] = declaredTextValue(spec.path ?? '', current, root);
    if (!found || value === null || value === undefined || value === '') return [];
    if (!Array.isArray(value)) throw new RuntimeError('output.emit for_each path must resolve to a list');
    const nestedLines = spec.lines ?? [String(spec.template ?? '{{}}')];
    return value.flatMap((item) => renderDeclaredTextLines(nestedLines, item, root));
  }}
  if (Object.prototype.hasOwnProperty.call(line, 'json')) {{
    const [found, value] = declaredTextValue(line.json, current, root);
    return declaredTextCanonicalJsonString(declaredTextCanonicalJsonValue(found ? value : null)).split('\\n');
  }}
  if (Object.prototype.hasOwnProperty.call(line, 'template')) return [renderDeclaredTextTemplate(String(line.template), current, root)];
  if (Object.prototype.hasOwnProperty.call(line, 'literal')) return [String(line.literal)];
  throw new RuntimeError('output.emit text view line object must declare when, for_each, json, template, or literal');
}}

function renderDeclaredTextTemplate(template, current, root) {{
  return String(template).replace(/\\{{([^}}]*)\\}}/g, (_match, token) => {{
    const [found, value] = declaredTextPlaceholderValue(String(token), current, root);
    return declaredTextFormat(found ? value : '');
  }});
}}

function declaredTextPlaceholderValue(token, current, root) {{
  const parts = String(token).split('|');
  let [found, value] = declaredTextValue(parts[0], current, root);
  for (const rawFilter of parts.slice(1)) {{
    const separatorIndex = rawFilter.indexOf(':');
    const name = separatorIndex === -1 ? rawFilter : rawFilter.slice(0, separatorIndex);
    const argument = separatorIndex === -1 ? '' : rawFilter.slice(separatorIndex + 1);
    if (name === 'len') {{
      value = Array.isArray(value) ? value.length : 0;
      found = true;
    }} else if (name === 'join') {{
      if (!found || value === null || value === undefined) {{
        value = '';
      }} else if (Array.isArray(value)) {{
        if (!value.every(declaredTextIsScalar)) throw new RuntimeError('output.emit join filter requires a list of JSON scalars');
        value = value.map(declaredTextFormatScalar).join(argument);
      }} else {{
        throw new RuntimeError('output.emit join filter requires a list');
      }}
      found = true;
    }} else if (name === 'empty') {{
      if (!declaredTextTruthy(value)) value = argument;
      found = true;
    }} else {{
      throw new RuntimeError(`unsupported output.emit text view filter: ${{name}}`);
    }}
  }}
  return [found, value];
}}

function declaredTextValue(path, current, root) {{
  const pathText = String(path ?? '');
  if (pathText === '' || pathText === '.') return [true, current];
  if (pathText.startsWith('root.')) return fieldByPath(root, pathText.slice('root.'.length));
  if (isObject(current)) {{
    const [found, value] = fieldByPath(current, pathText);
    if (found) return [true, value];
  }}
  return fieldByPath(root, pathText);
}}

function declaredTextTruthy(value) {{
  if (value === null || value === undefined) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (isObject(value)) return Object.keys(value).length > 0;
  if (typeof value === 'string') return value.length > 0;
  return Boolean(value);
}}

function declaredTextFormat(value) {{
  if (!declaredTextIsScalar(value)) throw new RuntimeError('output.emit text view placeholders require JSON scalars; use json lines for arrays or objects');
  return declaredTextFormatScalar(value);
}}

function declaredTextIsScalar(value) {{
  return value === null || value === undefined || ['string', 'boolean'].includes(typeof value) || declaredTextIsSafeInteger(value);
}}

function declaredTextIsSafeInteger(value) {{
  return typeof value === 'number' && Number.isSafeInteger(value);
}}

function declaredTextScalarEqual(actual, expected) {{
  if (expected === null || expected === undefined) return actual === null || actual === undefined;
  if (typeof expected === 'boolean') return typeof actual === 'boolean' && actual === expected;
  if (typeof expected === 'string') return typeof actual === 'string' && actual === expected;
  if (declaredTextIsSafeInteger(expected)) return declaredTextIsSafeInteger(actual) && actual === expected;
  return false;
}}

function declaredTextFormatScalar(value) {{
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (value === null || value === undefined) return '';
  if (declaredTextIsSafeInteger(value)) return String(value);
  return String(value);
}}

function declaredTextCanonicalJsonValue(value) {{
  if (Array.isArray(value)) return value.map(declaredTextCanonicalJsonValue);
  if (isObject(value)) {{
    const out = {{}};
    for (const key of Object.keys(value).sort()) out[key] = declaredTextCanonicalJsonValue(value[key]);
    return out;
  }}
  if (value === null || value === undefined || ['string', 'boolean'].includes(typeof value)) return value;
  if (declaredTextIsSafeInteger(value)) return value;
  if (typeof value === 'number') throw new RuntimeError('output.emit text view JSON numbers must be finite safe integers');
  return value;
}}

function declaredTextCanonicalJsonString(value, level = 0) {{
  const indent = '  '.repeat(level);
  const childIndent = '  '.repeat(level + 1);
  if (Array.isArray(value)) {{
    if (value.length === 0) return '[]';
    return '[\\n' + value.map((item) => `${{childIndent}}${{declaredTextCanonicalJsonString(item, level + 1)}}`).join(',\\n') + '\\n' + indent + ']';
  }}
  if (isObject(value)) {{
    const keys = Object.keys(value).sort();
    if (keys.length === 0) return '{{}}';
    return '{{\\n' + keys.map((key) => `${{childIndent}}${{JSON.stringify(key)}}: ${{declaredTextCanonicalJsonString(value[key], level + 1)}}`).join(',\\n') + '\\n' + indent + '}}';
  }}
  if (value === undefined) return 'null';
  return JSON.stringify(value);
}}

function limitedViewValue(value, limit) {{
  if (!Number.isInteger(limit) || typeof value === 'string') return value;
  if (Array.isArray(value)) return value.slice(0, Math.max(limit, 0));
  return value;
}}

function viewPayload(values, args) {{
  const sourceName = String(args.source ?? 'result');
  if (!Object.prototype.hasOwnProperty.call(values, sourceName)) throw new RuntimeError(`payload.view source value is missing: ${{sourceName}}`);
  const fields = stringList(args.fields ?? [], 'payload.view fields');
  if (args.limits !== undefined && !isObject(args.limits)) throw new RuntimeError('payload.view limits must be an object');
  const limits = args.limits ?? {{}};
  const payload = values[sourceName];
  const viewed = {{
    kind: String(args.view_kind ?? 'command-generation/payload-view/v1'),
    source_command: String(args.source_command ?? values.operation_id ?? ''),
    values: {{}}
  }};
  const missing = [];
  for (const field of fields) {{
    const [found, value] = fieldByPath(payload, field);
    if (found) viewed.values[field] = limitedViewValue(value, limits[field]);
    else missing.push(field);
  }}
  if (missing.length) viewed.missing = missing;
  return viewed;
}}

function transactionPlan(values, args) {{
  const resourcesFrom = String(args.resources_from ?? 'resources');
  const rawResources = values[resourcesFrom] ?? args.resources ?? [];
  if (!Array.isArray(rawResources)) throw new RuntimeError('transaction.plan resources must be a list');
  const defaultAction = String(args.default_action ?? 'write');
  const defaultKind = String(args.default_kind ?? 'file');
  const actions = rawResources.map((item) => {{
    if (typeof item === 'string') return {{ action: defaultAction, kind: defaultKind, path: validateResourcePath(item) }};
    if (!isObject(item)) throw new RuntimeError('transaction.plan resources must be strings or objects');
    const rawPath = item.path ?? item.relative_path;
    if (typeof rawPath !== 'string' || !rawPath) throw new RuntimeError('transaction.plan resource path is required');
    return {{
      action: String(item.action ?? defaultAction),
      kind: String(item.kind ?? defaultKind),
      path: validateResourcePath(rawPath)
    }};
  }});
  const targetRootValue = String(args.target_root_value ?? 'target_root');
  return {{
    kind: String(args.plan_kind ?? 'command-generation/transaction-plan/v1'),
    dry_run: true,
    target_root: String(values[targetRootValue] ?? ''),
    schema_ref: String(args.schema_ref ?? ''),
    actions,
    mutation_safety: {{
      apply_status: 'package-owned',
      apply_primitive: String(args.apply_primitive ?? ''),
      conflict_hooks: stringList(args.conflict_hooks ?? [], 'transaction.plan conflict_hooks'),
      provenance_hooks: stringList(args.provenance_hooks ?? [], 'transaction.plan provenance_hooks'),
      rule: 'Generic transaction planning is dry-run only; mutating apply remains an explicit package-domain primitive.'
    }}
  }};
}}

function validateResourcePath(path) {{
  const resourcePath = String(path).replace(/\\\\/g, '/');
  const parts = resourcePath.split('/');
  if (
    !resourcePath ||
    resourcePath.startsWith('/') ||
    /^[A-Za-z]:/.test(parts[0] ?? '') ||
    parts.some((part) => part === '' || part === '.' || part === '..')
  ) {{
    throw new RuntimeError(`transaction.plan resource path must be relative and stay inside resources: ${{path}}`);
  }}
  return resourcePath;
}}

function executeHostPrimitive(primitive, values, args, operationId) {{
{configured_host_primitive_call}  const hostPrimitive = globalThis.hostPrimitive;
  if (typeof hostPrimitive === 'function') return hostPrimitive(primitive, values, args, operationId);
  throw new RuntimeError(`unsupported native TypeScript primitive: ${{primitive}}`);
}}

function executeHostDomainOperation(operationId, values) {{
  if (typeof hostDomainOperation === 'function') return hostDomainOperation(operationId, values);
  throw new RuntimeError(`unsupported native TypeScript domain operation: ${{operationId}}`);
}}

function executePrimitive(primitive, values, args, operationId) {{
  if (primitive === 'typescript.domain.execute') return executeHostDomainOperation(String(args.operation_id ?? operationId), values);
  if (primitive === 'path.target_root.resolve') {{
    const targetRoot = resolve(String(values.target ?? '.'));
    if (args.must_exist && !existsSync(targetRoot)) throw new RuntimeError(`target root does not exist: ${{targetRoot}}`);
    if (args.must_be_dir && (!existsSync(targetRoot) || !statSync(targetRoot).isDirectory())) throw new RuntimeError(`target root is not a directory: ${{targetRoot}}`);
    return targetRoot;
  }}
  if (primitive === 'filesystem.exists') {{
    const path = resolveInside(valueRoot(args, values), String(args.path ?? ''));
    if (args.kind === 'file') return existsSync(path) && statSync(path).isFile();
    if (args.kind === 'directory') return existsSync(path) && statSync(path).isDirectory();
    return existsSync(path);
  }}
  if (primitive === 'filesystem.read') return readText(resolveInside(resourceRoot(String(args.root ?? '')), String(args.path ?? '')));
  if (primitive === 'filesystem.glob') return globFiles(valueRoot(args, values), String(args.pattern ?? '')).map((relative_path) => ({{ relative_path }}));
  if (primitive === 'json.parse') return JSON.parse(String(values[String(args.source ?? 'registry_text')]));
  if (primitive === 'payload.assemble') return assemblePayload(values, args);
  if (primitive === 'payload.view') return viewPayload(values, args);
  if (primitive === 'payload.project') return projectPayload(values, args);
  if (primitive === 'output.emit') return emitOutput(values, args);
  if (primitive === 'transaction.plan') return transactionPlan(values, args);
  return executeHostPrimitive(primitive, values, args, operationId);
}}

function operationFragments(operation) {{
  const rawFragments = operation?.ir_plan?.fragments ?? [];
  if (!Array.isArray(rawFragments)) throw new RuntimeError('operation ir_plan.fragments must be a list');
  const fragments = new Map();
  for (const fragment of rawFragments) {{
    if (!isObject(fragment)) throw new RuntimeError('operation ir_plan fragment must be an object');
    const fragmentId = String(fragment.id ?? '').trim();
    if (!fragmentId) throw new RuntimeError('operation ir_plan fragment id is required');
    if (fragments.has(fragmentId)) throw new RuntimeError(`duplicate operation ir_plan fragment: ${{fragmentId}}`);
    if (!Array.isArray(fragment.steps) || fragment.steps.length === 0) {{
      throw new RuntimeError(`operation ir_plan fragment ${{fragmentId}} must declare non-empty steps`);
    }}
    fragments.set(fragmentId, fragment.steps);
  }}
  return fragments;
}}

function expandOperationSteps(steps, fragments, stack = []) {{
  const expanded = [];
  for (const step of steps) {{
    if (!isObject(step)) throw new RuntimeError('operation ir_plan step must be an object');
    const uses = String(step.uses ?? '').trim();
    const usesFragment = String(step.uses_fragment ?? '').trim();
    if (uses && usesFragment) throw new RuntimeError(`step ${{String(step.id ?? uses)}} cannot declare both uses and uses_fragment`);
    if (usesFragment) {{
      if (step.arguments !== undefined && !(isObject(step.arguments) && Object.keys(step.arguments).length === 0)) {{
        throw new RuntimeError(`fragment step ${{String(step.id ?? usesFragment)}} cannot declare arguments`);
      }}
      if (step.outputs !== undefined && !(Array.isArray(step.outputs) && step.outputs.length === 0)) {{
        throw new RuntimeError(`fragment step ${{String(step.id ?? usesFragment)}} cannot declare outputs`);
      }}
      if (stack.includes(usesFragment)) throw new RuntimeError(`operation ir_plan fragment cycle: ${{[...stack, usesFragment].join(' -> ')}}`);
      if (!fragments.has(usesFragment)) throw new RuntimeError(`unknown operation ir_plan fragment: ${{usesFragment}}`);
      expanded.push(...expandOperationSteps(fragments.get(usesFragment), fragments, [...stack, usesFragment]));
      continue;
    }}
    if (!uses) throw new RuntimeError(`step ${{String(step.id ?? '<unknown>')}} must declare uses or uses_fragment`);
    expanded.push(step);
  }}
  return expanded;
}}

function runSteps(operation, values) {{
  const steps = operation?.ir_plan?.steps;
  if (!Array.isArray(steps) || steps.length === 0) throw new RuntimeError(`operation ${{operation?.id ?? '<unknown>'}} has no executable ir_plan.steps`);
  const fragments = operationFragments(operation);
  for (const step of expandOperationSteps(steps, fragments)) {{
    if (!conditionMatches(step.when, values)) continue;
    const result = executePrimitive(String(step.uses ?? ''), values, isObject(step.arguments) ? step.arguments : {{}}, String(operation.id ?? ''));
    storeStepResult(values, step.outputs ?? [], result);
  }}
  return values;
}}

function executeGeneratedOperationValues({{ operationId, operationPath, values }}) {{
  if (!operationId) throw new RuntimeError('generated command has no operation id');
  if (!operationPath) throw new RuntimeError(`operation ${{operationId}} has no operation resource path`);
  const resourcePath = resolveInside(resourcesRoot, operationPath);
  if (!existsSync(resourcePath)) throw new RuntimeError(`operation resource is missing: ${{operationPath}}`);
  const operation = readJson(resourcePath);
  return runSteps(operation, {{ ...values }});
}}

export function invokeGeneratedOperation({{ operationId, operationPath, values }}) {{
  const finalValues = executeGeneratedOperationValues({{ operationId, operationPath, values }});
  return finalValues.result ?? finalValues.emitted ?? emitOutput({{ ...finalValues, result: finalValues.result }});
}}

export function runGeneratedOperation({{ operationId, operationPath, values }}) {{
  const finalValues = executeGeneratedOperationValues({{ operationId, operationPath, values }});
  let output = finalValues.emitted ?? emitOutput({{ ...finalValues, result: finalValues.result }});
  if (typeof output !== 'string') output = `${{JSON.stringify(output, null, 2)}}\n`;
  writeSync(1, output);
  return 0;
}}
"""


def _typescript_host_primitive_support_module(
    *,
    source_path: str,
    regenerate_command: str,
    host_manifest: CommandGenerationHostManifest,
) -> str:
    if host_manifest.typescript_primitive_support_path is None:
        return ""
    support_label = _host_runtime_support_label(
        host_manifest=host_manifest,
        support_path=host_manifest.typescript_primitive_support_path,
    )
    support = host_manifest.typescript_primitive_support_path.read_text(
        encoding="utf-8"
    )
    return (
        "// Generated target-local host primitive support module.\n"
        f"// Source: {source_path}\n"
        f"// Host primitive support: {support_label}\n"
        f"// Regenerate with: {regenerate_command}\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        f"{support}"
    )


def _typescript_cli_module(
    package: dict[str, Any],
    target: dict[str, Any],
    maturity_levels: dict[str, dict[str, Any]],
    runtime_binding: dict[str, Any],
    *,
    repo_root: Path,
    source_path: str,
    regenerate_command: str,
) -> str:
    command_names = sorted(
        command["command"]["name"] for command in package["commands"]
    )
    rendered_commands = json.dumps(command_names)
    rendered_interfaces = json.dumps(
        _typescript_interface_payload(package), indent=2, sort_keys=True
    )
    native_operation_ids = sorted(_typescript_native_operation_ids(package))
    rendered_native_operation_ids = json.dumps(native_operation_ids)
    weak_agent_status = _weak_agent_routing_for_target(target, maturity_levels)
    recovery_command = f"{target['entrypoints'][0]} --help"
    boundary_summary = "TypeScript CLI boundary: generated parser, validation, and command execution are Node/TypeScript only."
    native_helpers = _typescript_native_runtime_helpers(
        recovery_command=recovery_command
    )
    return (
        "#!/usr/bin/env node\n"
        "// Generated runnable adapter.\n"
        f"// Source: {source_path}\n"
        f"// Program: {package['program']}\n"
        f"// Regenerate with: {regenerate_command}\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        "import { writeSync } from 'node:fs';\n"
        "import { runGeneratedOperation } from './runtime.mjs';\n\n"
        f"const supportedCommands = new Set({rendered_commands});\n"
        f"const nativeOperationIds = new Set({rendered_native_operation_ids});\n"
        f"const commandDefinitions = {rendered_interfaces};\n"
        "const commandByName = new Map(commandDefinitions.map((definition) => [definition.name, definition.interface]));\n"
        "const commandDefinitionByName = new Map(commandDefinitions.map((definition) => [definition.name, definition]));\n"
        "const argv = process.argv.slice(2);\n"
        "const command = argv[0];\n\n"
        "function optionFlags(option) {\n"
        "  return Array.isArray(option.flags) ? option.flags : [];\n"
        "}\n\n"
        "function interfaceOptions(iface) {\n"
        "  return Array.isArray(iface.options) ? iface.options : [];\n"
        "}\n\n"
        "function interfaceArguments(iface) {\n"
        "  return Array.isArray(iface.arguments) ? iface.arguments : [];\n"
        "}\n\n"
        "function interfaceSubcommands(iface) {\n"
        "  return Array.isArray(iface.subcommands) ? iface.subcommands : [];\n"
        "}\n\n"
        "function isHelpToken(token) {\n"
        "  return token === '--help' || token === '-h';\n"
        "}\n\n"
        "function printRootHelp() {\n"
        f"  console.log(`Usage: {target['entrypoints'][0]} <command> [options]`);\n"
        "  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);\n"
        f"  console.log('Weak-agent routing: {weak_agent_status}');\n"
        f"  console.log({boundary_summary!r});\n"
        "  console.log('Recovery: use a supported generated command or inspect the generated command contract.');\n"
        "}\n\n"
        "function printInterfaceHelp(path, iface) {\n"
        "  const argumentNames = interfaceArguments(iface).map((argument) => argument.nargs === '?' ? `[${argument.name}]` : `<${argument.name}>`);\n"
        "  const hasSubcommands = interfaceSubcommands(iface).length > 0;\n"
        "  const subcommandSuffix = hasSubcommands ? ' <subcommand>' : '';\n"
        "  const argumentSuffix = argumentNames.length ? ` ${argumentNames.join(' ')}` : '';\n"
        "  console.log(`Usage: ${path.join(' ')}${subcommandSuffix} [options]${argumentSuffix}`);\n"
        "  if (iface.help) console.log(String(iface.help));\n"
        "  const options = interfaceOptions(iface);\n"
        "  if (options.length) {\n"
        "    console.log('Options:');\n"
        "    for (const option of options) {\n"
        "      const choices = Array.isArray(option.choices) ? ` choices=${option.choices.join('|')}` : '';\n"
        "      const required = option.required === true ? ' required' : '';\n"
        "      console.log(`  ${optionFlags(option).join(', ')}${required}${choices}  ${option.help ?? ''}`);\n"
        "    }\n"
        "  }\n"
        "  const subcommands = interfaceSubcommands(iface);\n"
        "  if (subcommands.length) {\n"
        "    console.log('Subcommands:');\n"
        "    for (const subcommand of subcommands) {\n"
        "      console.log(`  ${subcommand.name}  ${subcommand.help ?? ''}`);\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        "function failValidation(message) {\n"
        "  console.error(`TypeScript CLI validation failed: ${message}`);\n"
        f"  console.error('Recovery: run {recovery_command} and choose a supported generated command or valid option.');\n"
        "  process.exit(2);\n"
        "}\n\n"
        "function validateChoice(spec, value, label) {\n"
        "  if (Array.isArray(spec.choices) && !spec.choices.includes(value)) {\n"
        "    failValidation(`${label} must be one of: ${spec.choices.join(', ')}`);\n"
        "  }\n"
        "  if (spec.type === 'integer' && !/^-?\\d+$/.test(value)) {\n"
        "    failValidation(`${label} must be an integer`);\n"
        "  }\n"
        "}\n\n"
        "function optionByFlag(iface, flag) {\n"
        "  return interfaceOptions(iface).find((option) => optionFlags(option).includes(flag));\n"
        "}\n\n"
        "function consumeOption(iface, option, tokens, index, seenOptions) {\n"
        "  const optionName = option.name ?? optionFlags(option)[0];\n"
        "  if (optionName) seenOptions.add(optionName);\n"
        "  if (option.action === 'store_true') return index + 1;\n"
        "  if (option.action === 'append') {\n"
        "    if (index + 1 >= tokens.length || isHelpToken(tokens[index + 1])) {\n"
        "      failValidation(`${optionFlags(option)[0]} requires a value`);\n"
        "    }\n"
        "    const value = String(tokens[index + 1]);\n"
        "    validateChoice(option, value, optionFlags(option)[0]);\n"
        "    return index + 2;\n"
        "  }\n"
        "  if (option.nargs === '*') {\n"
        "    let cursor = index + 1;\n"
        "    while (cursor < tokens.length && !String(tokens[cursor]).startsWith('-')) {\n"
        "      validateChoice(option, String(tokens[cursor]), optionFlags(option)[0]);\n"
        "      cursor += 1;\n"
        "    }\n"
        "    return cursor;\n"
        "  }\n"
        "  if (index + 1 >= tokens.length || isHelpToken(tokens[index + 1])) {\n"
        "    failValidation(`${optionFlags(option)[0]} requires a value`);\n"
        "  }\n"
        "  const value = String(tokens[index + 1]);\n"
        "  validateChoice(option, value, optionFlags(option)[0]);\n"
        "  return index + 2;\n"
        "}\n\n"
        "function validateInterface(iface, tokens, path) {\n"
        "  const seenOptions = new Set();\n"
        "  const positional = [];\n"
        "  let index = 0;\n"
        "  while (index < tokens.length) {\n"
        "    const token = String(tokens[index]);\n"
        "    if (isHelpToken(token)) {\n"
        "      printInterfaceHelp(path, iface);\n"
        "      process.exit(0);\n"
        "    }\n"
        "    if (token.startsWith('-')) {\n"
        "      const option = optionByFlag(iface, token);\n"
        "      if (!option) failValidation(`unknown option ${token} for ${path.join(' ')}`);\n"
        "      index = consumeOption(iface, option, tokens, index, seenOptions);\n"
        "      continue;\n"
        "    }\n"
        "    const subcommand = interfaceSubcommands(iface).find((candidate) => candidate.name === token);\n"
        "    if (subcommand) {\n"
        "      validateInterface(subcommand, tokens.slice(index + 1), [...path, token]);\n"
        "      return;\n"
        "    }\n"
        "    positional.push(token);\n"
        "    index += 1;\n"
        "  }\n"
        "  for (const option of interfaceOptions(iface)) {\n"
        "    const optionName = option.name ?? optionFlags(option)[0];\n"
        "    if (option.required === true && optionName && !seenOptions.has(optionName)) {\n"
        "      failValidation(`missing required option ${optionFlags(option)[0]} for ${path.join(' ')}`);\n"
        "    }\n"
        "  }\n"
        "  const positionalSpecs = interfaceArguments(iface);\n"
        "  const requiredPositionals = positionalSpecs.filter((argument) => argument.nargs !== '?' && argument.default === undefined);\n"
        "  if (positional.length < requiredPositionals.length) {\n"
        "    failValidation(`missing required argument for ${path.join(' ')}`);\n"
        "  }\n"
        "  if (positional.length > positionalSpecs.length) {\n"
        "    failValidation(`unexpected argument ${positional[positionalSpecs.length]} for ${path.join(' ')}`);\n"
        "  }\n"
        "  positional.forEach((value, position) => validateChoice(positionalSpecs[position] ?? {}, value, positionalSpecs[position]?.name ?? 'argument'));\n"
        "  if (interfaceSubcommands(iface).length && iface.subcommands_required !== false && positional.length === 0) {\n"
        "    failValidation(`missing subcommand for ${path.join(' ')}`);\n"
        "  }\n"
        "}\n\n"
        f"{native_helpers}"
        "if (!command || command === '--help' || command === '-h') {\n"
        "  printRootHelp();\n"
        "  process.exit(0);\n"
        "}\n\n"
        "if (!supportedCommands.has(command)) {\n"
        "  console.error(`Unsupported generated command: ${command}`);\n"
        f"  console.error('Recovery: run {recovery_command} and choose one of the supported generated commands.');\n"
        "  process.exit(2);\n"
        "}\n\n"
        "validateInterface(commandByName.get(command), argv.slice(1), [command]);\n\n"
        "maybeRunNativeOperation();\n"
    )


def _typescript_mock_runtime() -> str:
    return "const payload = {\n  command: process.argv[2],\n  args: process.argv.slice(2),\n};\nconsole.log(JSON.stringify(payload));\n"


def _typescript_required_option_case(package: dict[str, Any]) -> dict[str, Any] | None:
    def find_required(
        interface: dict[str, Any], path: list[str]
    ) -> dict[str, Any] | None:
        for option in interface.get("options", []):
            if isinstance(option, dict) and option.get("required") is True:
                flags = option.get("flags", [])
                if isinstance(flags, list) and flags:
                    return {"path": path, "flag": str(flags[0])}
        for subcommand in interface.get("subcommands", []):
            if isinstance(subcommand, dict) and subcommand.get("name"):
                found = find_required(subcommand, [*path, str(subcommand["name"])])
                if found is not None:
                    return found
        return None

    for command in package["commands"]:
        found = find_required(command["interface"], [str(command["command"]["name"])])
        if found is not None:
            return found
    return None


def _typescript_sample_value(spec: dict[str, Any], *, fallback: str) -> str:
    choices = spec.get("choices", [])
    if isinstance(choices, list) and choices:
        preferred_by_name = {
            "format": "json",
            "priority": "high",
        }
        preferred = preferred_by_name.get(str(spec.get("name", "")))
        if preferred in choices:
            return preferred
        default = spec.get("default")
        if default in choices:
            return str(default)
        return str(choices[0])
    if spec.get("type") == "integer":
        default = spec.get("default")
        if isinstance(default, int):
            return str(default)
        if isinstance(default, str) and default.strip().lstrip("-").isdigit():
            return default
        return "1"
    default = spec.get("default")
    if isinstance(default, str) and default:
        return default
    sample_by_name = {
        "project": "alpha",
        "target": ".",
        "target_root": ".",
    }
    return sample_by_name.get(str(spec.get("name", "")), fallback)


def _typescript_option_flag(option: dict[str, Any]) -> str:
    flags = option.get("flags", [])
    if isinstance(flags, list) and flags:
        return str(flags[0])
    name = str(option.get("name", "")).strip()
    return f"--{name.replace('_', '-')}" if name else ""


def _typescript_sample_invocations(command: dict[str, Any]) -> dict[str, Any]:
    command_name = str(command.get("command", {}).get("name", "")).strip()
    interface = command.get("interface", {})
    if not command_name or not isinstance(interface, dict):
        return {
            "json_args": [],
            "spaced_args": [],
            "path": [],
            "requires_subcommand": False,
            "format_path": [],
        }
    path = [command_name]
    current = interface
    requires_subcommand = False
    while True:
        subcommands = [
            item for item in current.get("subcommands", []) if isinstance(item, dict)
        ]
        subcommands_required = bool(
            subcommands and current.get("subcommands_required") is not False
        )
        if not subcommands_required:
            break
        first_subcommand = sorted(
            subcommands, key=lambda item: str(item.get("name", ""))
        )[0]
        subcommand_name = str(first_subcommand.get("name", "")).strip()
        if not subcommand_name:
            break
        path.append(subcommand_name)
        current = first_subcommand
        requires_subcommand = True

    required_positionals = [
        item
        for item in current.get("arguments", [])
        if isinstance(item, dict)
        and item.get("nargs") != "?"
        and item.get("default") is None
    ]
    required_options = [
        item
        for item in current.get("options", [])
        if isinstance(item, dict) and item.get("required") is True
    ]
    json_args = list(path)
    spaced_args: list[str] = []
    spaced_arg_index: int | None = None
    for argument in required_positionals:
        value = _typescript_sample_value(
            argument, fallback=str(argument.get("name") or "value")
        )
        if spaced_arg_index is None and argument.get("type") != "integer":
            spaced_arg_index = len(json_args)
        json_args.append(value)
    for option in required_options:
        flag = _typescript_option_flag(option)
        if not flag:
            continue
        if option.get("action") == "store_true":
            json_args.append(flag)
            continue
        value = _typescript_sample_value(option, fallback="value")
        if spaced_arg_index is None and option.get("type") != "integer":
            spaced_arg_index = len(json_args) + 1
        json_args.extend([flag, value])
    if spaced_arg_index is not None:
        spaced_args = list(json_args)
        spaced_args[spaced_arg_index] = "__SPACED_TARGET__"
    format_option = next(
        (
            item
            for item in current.get("options", [])
            if isinstance(item, dict)
            and item.get("name") == "format"
            and _typescript_option_flag(item)
        ),
        None,
    )
    format_path = list(json_args)
    if format_option is not None:
        json_args.extend(
            [
                _typescript_option_flag(format_option),
                _typescript_sample_value(format_option, fallback="json"),
            ]
        )
    dry_run_option = next(
        (
            item
            for item in current.get("options", [])
            if isinstance(item, dict)
            and item.get("name") == "dry_run"
            and _typescript_option_flag(item)
        ),
        None,
    )
    if dry_run_option is not None:
        flag = _typescript_option_flag(dry_run_option)
        json_args.insert(len(path), flag)
        if spaced_args:
            spaced_args.insert(len(path), flag)
    return {
        "json_args": json_args,
        "spaced_args": spaced_args,
        "path": path,
        "requires_subcommand": requires_subcommand,
        "format_path": format_path,
    }


def _typescript_test(package: dict[str, Any], target: dict[str, Any]) -> str:
    expected_commands = sorted(
        command["command"]["name"] for command in package["commands"]
    )
    rendered_expected = json.dumps(expected_commands)
    sample_command = expected_commands[0]
    sample_command_record = next(
        command
        for command in package["commands"]
        if command["command"]["name"] == sample_command
    )
    sample_invocations = _typescript_sample_invocations(sample_command_record)
    sample_path = sample_invocations["path"]
    sample_requires_subcommand = bool(sample_invocations["requires_subcommand"])
    sample_json_args = sample_invocations["json_args"]
    sample_spaced_args = sample_invocations["spaced_args"]
    sample_format_path = sample_invocations["format_path"]
    required_case = _typescript_required_option_case(package)
    runnable = _is_runnable_typescript_target(target)
    expected_maturity = target["maturity_level_ref"]
    expected_generation_status = target["generation_status"]
    if target.get("maturity_level_ref") == "weak-agent-safe-adapter":
        expected_weak_agent_routing = "allowed-read-only"
    elif target.get("maturity_level_ref") == "mutation-capable-adapter":
        expected_weak_agent_routing = "allowed-mutation-with-review"
    else:
        expected_weak_agent_routing = "review-required"
    boundary_help_assertions = (
        "  assert.match(result.stdout, /Node\\/TypeScript only/);\n"
        "  assert.doesNotMatch(result.stdout, /Python runtime handoff/);\n"
    )
    imports = (
        "import assert from 'node:assert/strict';\nimport test from 'node:test';\n"
    )
    if runnable:
        imports += "import { spawnSync } from 'node:child_process';\nimport { fileURLToPath } from 'node:url';\n"
    imports += "import { mkdirSync, readFileSync, rmSync } from 'node:fs';\n"
    body = imports + (
        "\n"
        "const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');\n"
        "const commandPackage = JSON.parse(readFileSync(new URL('../resources/command_package.json', import.meta.url), 'utf8'));\n"
        "const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));\n"
        "\n"
        "test('generated package resource exposes expected commands', () => {\n"
        f"  const expected = {rendered_expected};\n"
        "  assert.deepEqual(commandPackage.commands.map((command) => command.command.name).sort(), expected);\n"
        "  assert.match(source, /resources\\/command_package\\.json/);\n"
        "  assert.doesNotMatch(source, /adapter_id/);\n"
        "  assert.deepEqual(packageJson.files, ['src', 'resources']);\n"
        "});\n"
        "\n"
        "test('generated package metadata exposes maturity and weak-agent routing status', () => {\n"
        "  const metadata = packageJson.agenticWorkspace;\n"
        f"  assert.equal(metadata.generationStatus, {expected_generation_status!r});\n"
        f"  assert.equal(metadata.maturity.id, {expected_maturity!r});\n"
        "  assert.equal(typeof metadata.maturity.summary, 'string');\n"
        "  assert.ok(metadata.maturity.summary.length > 0);\n"
        "  assert.ok(Array.isArray(metadata.maturity.promotion_requires));\n"
        "  assert.ok(metadata.maturity.promotion_requires.length > 0);\n"
    )
    if runnable:
        body += (
            "  assert.equal(metadata.fixtureOnly, false);\n"
            "  assert.equal(metadata.maturity.runnable, true);\n"
            f"  assert.equal(metadata.maturity.weak_agent_routing, {expected_weak_agent_routing!r});\n"
            "  assert.ok(packageJson.bin);\n"
        )
    else:
        body += (
            "  assert.equal(metadata.fixtureOnly, true);\n"
            "  assert.equal(metadata.maturity.runnable, false);\n"
            "  assert.equal(metadata.maturity.weak_agent_routing, 'forbidden');\n"
            "  assert.equal(packageJson.bin, undefined);\n"
        )
    body += "});\n"
    if runnable:
        body += (
            "\n"
            "test('generated runnable adapter executes supported command without Python runtime', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            f"  const result = spawnSync(process.execPath, [cli, ...{json.dumps(sample_json_args)}], {{ encoding: 'utf8' }});\n"
            "  assert.equal(result.status, 0);\n"
            "  const payload = JSON.parse(result.stdout);\n"
            "  assert.equal(typeof payload, 'object');\n"
            "  assert.equal(result.stderr, '');\n"
            "});\n"
        )
        if sample_spaced_args:
            body += (
                "\n"
                "test('generated runnable adapter preserves spaced argv values during native execution', () => {\n"
                "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
                "  const spacedTarget = fileURLToPath(new URL('../tmp target with spaces', import.meta.url));\n"
                "  mkdirSync(spacedTarget, { recursive: true });\n"
                "  try {\n"
                f"    const args = {json.dumps(sample_spaced_args)}.map((token) => token === '__SPACED_TARGET__' ? spacedTarget : token);\n"
                "    const result = spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8' });\n"
                "    assert.equal(result.status, 0);\n"
                "    assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
                "  } finally {\n"
                "    rmSync(spacedTarget, { recursive: true, force: true });\n"
                "  }\n"
                "});\n"
            )
        if sample_requires_subcommand:
            body += (
                "\n"
                "test('generated runnable adapter rejects command without required subcommand', () => {\n"
                "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
                f"  const result = spawnSync(process.execPath, [cli, ...{json.dumps([sample_command])}], {{ encoding: 'utf8' }});\n"
                "  assert.equal(result.status, 2);\n"
                "  assert.equal(result.stdout, '');\n"
                f"  assert.match(result.stderr, /missing subcommand for {sample_command}/);\n"
                "  assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
                "});\n"
            )
        body += (
            "\n"
            "test('generated runnable adapter exposes routing status and recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const result = spawnSync(process.execPath, [cli, '--help'], { encoding: 'utf8' });\n"
            "  assert.equal(result.status, 0);\n"
            "  assert.match(result.stdout, /Supported generated commands:/);\n"
            f"  assert.match(result.stdout, /Weak-agent routing: {expected_weak_agent_routing}/);\n"
            f"{boundary_help_assertions}"
            "  assert.match(result.stdout, /Recovery:/);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter renders command help without executing runtime', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            f"  const result = spawnSync(process.execPath, [cli, ...{json.dumps(sample_path)}, '--help'], {{\n"
            "    encoding: 'utf8',\n"
            "  });\n"
            "  assert.equal(result.status, 0);\n"
            "  assert.match(result.stdout, /Usage:/);\n"
            "  assert.match(result.stdout, /Options:/);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter validates choices before command execution', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            f"  const result = spawnSync(process.execPath, [cli, ...{json.dumps(sample_format_path)}, '--format', '__invalid__'], {{\n"
            "    encoding: 'utf8',\n"
            "  });\n"
            "  assert.equal(result.status, 2);\n"
            "  assert.equal(result.stdout, '');\n"
            "  assert.match(result.stderr, /TypeScript CLI validation failed:/);\n"
            "  assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
            "});\n"
        )
        if required_case is not None:
            body += (
                "\n"
                "test('generated runnable adapter validates required options before command execution', () => {\n"
                "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
                f"  const result = spawnSync(process.execPath, [cli, ...{json.dumps(required_case['path'])}], {{\n"
                "    encoding: 'utf8',\n"
                "  });\n"
                "  assert.equal(result.status, 2);\n"
                "  assert.equal(result.stdout, '');\n"
                f"  assert.match(result.stderr, /missing required option {required_case['flag']}/);\n"
                "  assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
                "});\n"
            )
        body += (
            "\n"
            "test('generated runnable adapter rejects unsupported commands with recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const result = spawnSync(process.execPath, [cli, '__unsupported__'], { encoding: 'utf8' });\n"
            "  assert.equal(result.status, 2);\n"
            "  assert.equal(result.stdout, '');\n"
            "  assert.match(result.stderr, /Unsupported generated command: __unsupported__/);\n"
            "  assert.match(result.stderr, /Recovery:/);\n"
            "});\n"
        )
    return body


def _target_scoped_package_resource(
    package: dict[str, Any], target: dict[str, Any], *, manifest_schema_version: str
) -> dict[str, Any]:
    scoped = package_resource_with_generation_metadata(
        package,
        manifest_schema_version=manifest_schema_version,
        target=target,
        target_layout_version=TYPESCRIPT_TARGET_LAYOUT_VERSION,
    )
    scoped["targets"] = [dict(target)]
    if target.get("kind") != "python":
        scoped.pop("python_runtime_binding", None)
    scoped["target_resource_scope"] = {
        "kind": "command-generation/target-scoped-package-resource/v1",
        "target_kind": str(target.get("kind", "")),
        "target_package_name": str(target.get("package_name", "")),
        "rule": "Target resources carry universal command/operation metadata plus only this target's runtime binding.",
    }
    return scoped


def render_typescript_outputs(
    package: dict[str, Any],
    target: dict[str, Any],
    *,
    repo_root: Path,
    root: Path,
    maturity_levels: dict[str, dict[str, Any]],
    runtime_binding: dict[str, Any],
    manifest_schema_version: str,
    source_path: str,
    regenerate_command: str,
    host_manifest: CommandGenerationHostManifest,
) -> list[GeneratedOutput]:
    outputs = [
        GeneratedOutput(
            root / "package.json",
            _typescript_package_json(
                package,
                target,
                maturity_levels[target["maturity_level_ref"]],
                runtime_binding,
                manifest_schema_version=manifest_schema_version,
                source_path=source_path,
            ),
        ),
        GeneratedOutput(
            root / "src" / "commandPackage.ts",
            _typescript_module(
                package, source_path=source_path, regenerate_command=regenerate_command
            ),
        ),
        GeneratedOutput(
            root / "resources" / "command_package.json",
            _json_block(
                _target_scoped_package_resource(
                    package, target, manifest_schema_version=manifest_schema_version
                )
            )
            + "\n",
        ),
    ]
    outputs.extend(
        _typescript_resource_copy_outputs(
            package, repo_root=repo_root, root=root, host_manifest=host_manifest
        )
    )
    outputs.append(
        GeneratedOutput(
            root / "test" / "command-package.test.mjs",
            _typescript_test(package, target),
        )
    )
    if _is_runnable_typescript_target(target):
        outputs.append(
            GeneratedOutput(
                root / "src" / "runtime.mjs",
                _typescript_runtime_module(
                    source_path=source_path,
                    regenerate_command=regenerate_command,
                    host_manifest=host_manifest,
                ),
            )
        )
        if host_manifest.typescript_primitive_support_path is not None:
            outputs.append(
                GeneratedOutput(
                    root / "src" / "hostPrimitiveSupport.mjs",
                    _typescript_host_primitive_support_module(
                        source_path=source_path,
                        regenerate_command=regenerate_command,
                        host_manifest=host_manifest,
                    ),
                )
            )
        outputs.append(
            GeneratedOutput(
                root / "src" / "cli.mjs",
                _typescript_cli_module(
                    package,
                    target,
                    maturity_levels,
                    runtime_binding,
                    repo_root=repo_root,
                    source_path=source_path,
                    regenerate_command=regenerate_command,
                ),
            )
        )
    return outputs
