Finish the Agentic Workspace bootstrap in C:/Users/ricka/Documents/src/command-generation.

Repo state:
- blank_or_unmanaged_repo

Inferred policy:
- install_direct

Lifecycle mode:
- install

Selected modules:
- planning
- memory

Intent:
- confirmed: set up this repo for both Planning and Memory
- interpreted: set up this repo for both Planning and Memory

The CLI already:
- created .agentic-workspace/docs/execution-flow-contract.md
- created .agentic-workspace/docs/lifecycle-and-config-contract.md
- created .agentic-workspace/docs/minimum-operating-model.md
- created .agentic-workspace/docs/routing-contract.md
- created .agentic-workspace/docs/system-intent-contract.md
- created .agentic-workspace/docs/workspace-config-contract.md
- created .agentic-workspace/planning/UPGRADE-SOURCE.toml
- created .agentic-workspace/planning/agent-manifest.json
- created .agentic-workspace/planning/decompositions/README.md
- created .agentic-workspace/planning/decompositions/TEMPLATE.decomposition.json
- created .agentic-workspace/planning/execplans/README.md
- created .agentic-workspace/planning/execplans/TEMPLATE.plan.json
- created .agentic-workspace/planning/execplans/archive/README.md
- created .agentic-workspace/planning/schemas/planning-decomposition.schema.json
- created .agentic-workspace/planning/schemas/planning-execplan.schema.json
- created .agentic-workspace/planning/schemas/planning-external-intent-evidence.schema.json
- created .agentic-workspace/planning/schemas/planning-finished-work-evidence.schema.json
- created .agentic-workspace/planning/schemas/planning-review.schema.json
- created AGENTS.md
- created .agentic-workspace/planning/skills/bootstrap-upgrade/SKILL.md
- created .agentic-workspace/planning/skills/planning-assurance-delegation/SKILL.md
- created .agentic-workspace/planning/skills/planning-autopilot/SKILL.md
- created .agentic-workspace/planning/skills/planning-closeout-trust/SKILL.md
- created .agentic-workspace/planning/skills/planning-decompose/SKILL.md
- created .agentic-workspace/planning/skills/planning-high-assurance-lifecycle/SKILL.md
- created .agentic-workspace/planning/skills/planning-intake-upstream-task/SKILL.md
- created .agentic-workspace/planning/skills/planning-intent-verification/SKILL.md
- created .agentic-workspace/planning/skills/planning-new-plan-tighten/SKILL.md
- created .agentic-workspace/planning/skills/planning-orchestrator-workflow/SKILL.md
- created .agentic-workspace/planning/skills/planning-promote-review-findings/SKILL.md
- created .agentic-workspace/planning/skills/planning-reporting/SKILL.md
- created .agentic-workspace/planning/skills/planning-review-pass/SKILL.md
- created .agentic-workspace/planning/skills/README.md
- created .agentic-workspace/planning/skills/REGISTRY.json
- created .agentic-workspace/docs/installer-behavior.md
- created .agentic-workspace/docs/memory-metadata-contract.md
- created .agentic-workspace/memory/bootstrap/README.md
- created .agentic-workspace/memory/bootstrap/skills/cleanup/agents/openai.yaml
- created .agentic-workspace/memory/bootstrap/skills/cleanup/SKILL.md
- created .agentic-workspace/memory/bootstrap/skills/install/agents/openai.yaml
- created .agentic-workspace/memory/bootstrap/skills/install/SKILL.md
- created .agentic-workspace/memory/bootstrap/skills/REGISTRY.json
- created .agentic-workspace/memory/repo/decisions/README.md
- created .agentic-workspace/memory/repo/domains/README.md
- created .agentic-workspace/memory/repo/index.md
- created .agentic-workspace/memory/repo/invariants/README.md
- created .agentic-workspace/memory/repo/manifest.toml
- created .agentic-workspace/memory/repo/runbooks/README.md
- created .agentic-workspace/memory/repo/templates/invariant.template.md
- created .agentic-workspace/memory/repo/templates/memory-note.template.md
- created .agentic-workspace/memory/repo/templates/runbook.template.md
- created .agentic-workspace/memory/skills/memory-capture/agents/openai.yaml
- created .agentic-workspace/memory/skills/memory-capture/SKILL.md
- created .agentic-workspace/memory/skills/memory-consultation-and-residue/agents/openai.yaml
- created .agentic-workspace/memory/skills/memory-consultation-and-residue/SKILL.md
- created .agentic-workspace/memory/skills/memory-hygiene/agents/openai.yaml
- created .agentic-workspace/memory/skills/memory-hygiene/SKILL.md
- created .agentic-workspace/memory/skills/memory-refresh/agents/openai.yaml
- created .agentic-workspace/memory/skills/memory-refresh/SKILL.md
- created .agentic-workspace/memory/skills/memory-router/agents/openai.yaml
- created .agentic-workspace/memory/skills/memory-router/SKILL.md
- created .agentic-workspace/memory/skills/memory-upgrade/agents/openai.yaml
- created .agentic-workspace/memory/skills/memory-upgrade/SKILL.md
- created .agentic-workspace/memory/skills/README.md
- created .agentic-workspace/memory/skills/REGISTRY.json
- created .agentic-workspace/memory/SKILLS.md
- created .agentic-workspace/memory/UPGRADE-SOURCE.toml
- created .agentic-workspace/memory/VERSION.md
- created .agentic-workspace/memory/WORKFLOW.md
- created .agentic-workspace/config.toml
- created .agentic-workspace/WORKFLOW.md
- created .agentic-workspace/OWNERSHIP.toml
- created .agentic-workspace/docs/module-map.md
- created .agentic-workspace/skills/REGISTRY.json
- created .agentic-workspace/skills/workspace-startup/SKILL.md
- created .agentic-workspace/skills/workspace-intent-discovery/SKILL.md
- created .agentic-workspace/skills/workspace-work-shape/SKILL.md
- created .agentic-workspace/skills/workspace-proof-selection/SKILL.md
- created .agentic-workspace/skills/workspace-transition-gates/SKILL.md
- created .agentic-workspace/skills/workspace-operating-loop/SKILL.md
- created .agentic-workspace/skills/workspace-setup-jumpstart/SKILL.md
- created .agentic-workspace/system-intent/WORKFLOW.md
- created .agentic-workspace/AGENTS.md
- created .agentic-workspace/local/scratch
- refreshed AGENTS.md
- preserved AGENTS.md

Review and finish:
- .agentic-workspace/WORKFLOW.md: shared Workspace layer is not installed; ordinary host-repo lifecycle should run through `agentic-workspace init --preset planning` or `agentic-workspace upgrade --modules planning`. Direct `agentic-planning` lifecycle commands are module-level maintenance/debugging surfaces and do not provide the full Workspace startup router, shared config, ownership, skills, or combined reports.
- .agentic-workspace/WORKFLOW.md: shared Workspace layer is not installed; ordinary host-repo lifecycle should run through `agentic-workspace init --preset memory` or `agentic-workspace upgrade --modules memory`. Direct `agentic-memory` lifecycle commands are module-level maintenance/debugging surfaces and do not provide the full Workspace startup router, shared config, ownership, skills, or combined reports.

Rules:
- keep agentic-workspace as the lifecycle entrypoint; do not improvise package-level install flows
- do not overwrite preserved repo-owned surfaces blindly
- prefer conservative merge over replacement when existing docs overlap
- do not edit generated files manually when a canonical source exists
- keep planning and memory boundaries explicit
- avoid creating duplicate source-of-truth workflow surfaces
- workflow artifact profile `repo-owned`: .agentic-workspace/planning/state.toml and .agentic-workspace/planning/execplans stay authoritative; no extra runtime artifact should carry durable state.
- keep the finishing pass non-interactive; do not assume a human can answer prompts or unblock a PTY

Validation:
- agentic-workspace doctor --target C:/Users/ricka/Documents/src/command-generation
- agentic-workspace status --target C:/Users/ricka/Documents/src/command-generation

When done:
- leave only durable workflow residue; do not keep temporary bootstrap notes around
- keep AGENTS.md as the repo startup entrypoint
