# START HERE

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Last updated:** 2026-03-07

This file is the *entry point* for a collaborator or coding agent when starting a new project using this PRD template.

## Mandatory reads (in order)
1. `PRD.md`
2. `TEMPLATE_EDIT_POLICY.md`
3. `PRD_READY_CHECKLIST.md`
4. `00_conventions/conventions_and_naming.md`
5. `00_conventions/prd_structure_and_ids.md`
6. `00_conventions/task_tracking_policy.md`
7. `05_coding_agent/prd_authoring_playbook.md`

## Quick start (first 30 minutes)
1. Fill `01_product/product_brief.md`.
2. Fill `01_product/kpis.md` and `01_product/roadmap.md`.
3. Record assumptions in `01_product/risks_and_assumptions.md`.
4. Record unresolved items in `01_product/open_questions.md`.
5. Create the current phase scope in `02_tasks/phases/Pxx_*.md`.
6. Populate `02_tasks/tasks_now.md` with actionable items.
7. Draft minimal architecture: `10_architecture/overview.md` + `10_architecture/main_flows.md`.
8. Fill the first architecture contracts that reduce ambiguity:
   - `10_architecture/package_layout.md`
   - `10_architecture/module_boundaries.md`
   - `10_architecture/configuration_strategy.md`
   - `10_architecture/external_dependencies.md`
9. Create the first traceability rows in `03_traceability/requirements_traceability_matrix.md`.
10. For each MVP feature: create `30_feature/F###_<name>.md` from the template.
11. Add verification commands in `90_quality/testing.md` and the first rows in `90_quality/validation_matrix.md`.

## Non-negotiable rules
- Do **not** edit files marked **LOCKED (template)** inside a project PRD.
- Do **not** hide project decisions in `95_sources/`.
- Do **not** leave requirements untraceable.
- Every planned deliverable MUST have a verification path.

## If something is missing
- Make a reasonable default.
- Mark it as `TODO`.
- Add it to `01_product/open_questions.md`.
- Reflect the gap in `02_tasks/tasks_now.md`.
