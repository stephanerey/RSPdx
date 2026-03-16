# PRD

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.


**Status:** Draft  
**Owner:** <your name>  
**Last updated:** 2026-02-12

## What this PRD is
This PRD is the *single entry point* for the project specification. It links to stable conventions, product framing, phase/task tracking, architecture, feature specs, and quality gates.

## How to use
1. Read: `00_conventions/README.md` → `00_conventions/conventions_and_naming.md`
2. Fill: `01_product/product_brief.md` (+ KPIs/risks/roadmap)
3. Start a phase: `02_tasks/phases/P00_bootstrap.md` then drive execution via `02_tasks/tasks_now.md`
4. Use the agent prompts: `05_coding_agent/README.md`
5. Maintain: architecture docs under `10_architecture/`
6. Specify features under `30_feature/` (one spec per feature, with IDs)
7. Apply DoD / tests / NFR under `90_quality/`
8. Drop raw inputs under `95_sources/` and keep `95_sources/index.md` annotated.

## Index

- `START_HERE.md`
- `PRD_READY_CHECKLIST.md`

### Always-read (stable)
- `00_conventions/README.md`
- `00_conventions/conventions_and_naming.md`
- `00_conventions/prd_structure_and_ids.md`
- `90_quality/definition_of_done.md`
- `90_quality/quality_gate_checklist.md` (optional)

### Product (living)
- `01_product/product_brief.md`
- `01_product/kpis.md`
- `01_product/risks_and_assumptions.md`
- `01_product/roadmap.md`
- `01_product/decisions.md` (optional)

### Tasks / phases (living + snapshots)
- `02_tasks/tasks_now.md`
- `02_tasks/phases/` (phase scopes)
- `02_tasks/snapshots/` (immutable checkpoints)

### Coding agent (prompts + handoff)
- `05_coding_agent/prd_authoring_playbook.md`
- `05_coding_agent/base_prompt.md`
- `05_coding_agent/phases/` (phase prompts)
- `05_coding_agent/handoffs/` (handoff templates)
- `05_coding_agent/plans/` (execution plan template)

### Architecture
- `10_architecture/overview.md`
- `10_architecture/main_flows.md`
- `10_architecture/runtime_environment.md`
- `10_architecture/environments_and_deployment.md`
- `10_architecture/package_layout.md`
- `10_architecture/module_boundaries.md`
- `10_architecture/data_and_paths.md`
- `10_architecture/data_schema.md`
- `10_architecture/logging_and_errors.md`
- `10_architecture/security_and_auth.md` (optional)

### Refactor (optional)
- `20_refactor/overview.md`
- `20_refactor/refactor_plan_template.md`
- `20_refactor/arch_cleanup_template.md`
- `20_refactor/thread_manager_spec.md` (optional)
- `20_refactor/ui_modularization.md` (optional)

### Features
- `30_feature/feature_spec_guidelines.md`
- `30_feature/feature_template.md`
- `30_feature/api_spec_template.md`
- `30_feature/feature_index.md` (optional)

### Sources (inputs)
- `95_sources/README.md`
- `95_sources/index.md`
- `95_sources/links.md`
