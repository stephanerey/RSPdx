# START HERE

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.

**Last updated:** 2026-03-12

This file is the entry point for a human collaborator or coding agent starting from this template.

## Mandatory reads (in order)
1. `README_FOR_HUMANS.md`
2. `PROJECT_INTAKE.md`
3. `PRD.md`
4. `TEMPLATE_EDIT_POLICY.md`
5. `PROJECT_PROFILE.md`
6. `PACKS_ACTIVE.md`
7. `PRD_READY_CHECKLIST.md`
8. `00_conventions/conventions_and_naming.md`
9. `00_conventions/prd_structure_and_ids.md`
10. `00_conventions/task_tracking_policy.md`
11. `05_coding_agent/prd_authoring_playbook.md`

## Quick start for a new project
1. Fill `PROJECT_INTAKE.md` manually or generate it from the intake wizard.
2. Fill `PROJECT_PROFILE.md`.
3. Fill `01_product/product_brief.md`.
4. Fill `01_product/kpis.md` and `01_product/roadmap.md`.
5. Record assumptions and risks in `01_product/risks_and_assumptions.md`.
6. Record unresolved items in `01_product/open_questions.md`.
7. Create explicit requirements in `04_requirements/requirements_catalog.md`.
8. Add major use cases to `04_requirements/use_cases.md`.
9. Select the current phase in `02_tasks/phases/Pxx_*.md`.
10. Populate `02_tasks/tasks_now.md` with actionable items.
11. Draft minimal architecture in `10_architecture/overview.md` and `10_architecture/main_flows.md`.
12. Fill `03_traceability/requirements_traceability_matrix.md`.
13. For each planned feature, create `30_feature/F###_<name>.md` from the template.
14. Add verification commands in `90_quality/testing.md` and rows in `90_quality/validation_matrix.md`.
15. Import relevant packs into `40_active_packs/`.
16. Register the imported packs in `PACKS_ACTIVE.md`.
17. Reflect the imported pack guidance into the core docs.

## Non-negotiable rules
- Do **not** edit files marked **LOCKED (template)** inside a project PRD.
- Do **not** hide project decisions in `95_sources/`.
- Do **not** leave requirements untraceable.
- Packs are guidance layers, not the main source of truth.
- Every planned deliverable MUST have a verification path.

## Optional Codex bootstrap
If this project will be worked on with Codex, instantiate the starter files from `../tools/codex/templates/` in the repository that will host the code.
Keep repository rules in `AGENTS.md`, and keep project truth in the PRD.
