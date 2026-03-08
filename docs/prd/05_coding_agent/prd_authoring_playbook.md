# PRD Authoring Playbook (for the assistant / agent)

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Last updated:** 2026-03-07

## Purpose
This document defines the *methodology* to create or update a PRD using this template.
It is written for a human collaborator or a coding agent.

## Operating principles
- Prefer **explicit decisions** over implicit assumptions.
- If information is missing, make a **reasonable default**, mark it as `TODO`, and list it under `01_product/open_questions.md`.
- Keep documents **short and testable**.
- Every deliverable MUST have **verification steps**.
- Keep **traceability** updated, not just tasks.

## Workflow (recommended)

### Step 0 — Initialize baseline
1. Ensure folder structure matches the template.
2. Read mandatory docs:
   - `PRD.md`
   - `TEMPLATE_EDIT_POLICY.md`
   - `00_conventions/conventions_and_naming.md`
   - `00_conventions/prd_structure_and_ids.md`
   - `00_conventions/task_tracking_policy.md`
   - `90_quality/definition_of_done.md`

### Step 1 — Product framing
Fill:
- `01_product/product_brief.md`
- `01_product/kpis.md`
- `01_product/risks_and_assumptions.md`
- `01_product/open_questions.md`
- `01_product/roadmap.md`

Rule: if a requirement is not reflected in the product docs, it is not committed.

### Step 2 — Traceability baseline
Fill:
- `03_traceability/requirements_traceability_matrix.md`

Rule: core requirements SHOULD have stable IDs and a verification path.

### Step 3 — Phase planning and tasks
1. Select the current phase `Pxx`.
2. Define the phase scope in `02_tasks/phases/Pxx_*.md`.
3. Populate `02_tasks/tasks_now.md` with actionable items.

### Step 4 — Architecture contract
Fill the minimum set:
- `10_architecture/overview.md`
- `10_architecture/main_flows.md`
- `10_architecture/runtime_environment.md`
- `10_architecture/package_layout.md`
- `10_architecture/module_boundaries.md`
- `10_architecture/configuration_strategy.md`
- `10_architecture/external_dependencies.md`

Create ADRs under `10_architecture/adr/` when decisions are technical and durable.

### Step 5 — Feature, API, and interface specs
For each feature:
1. Create `30_feature/F###_<short_name>.md`.
2. If there is an HTTP/RPC surface: create `API###`.
3. If there is a non-HTTP contract: create `IFC###`.

### Step 6 — Quality gates
Fill:
- `90_quality/testing.md`
- `90_quality/validation_matrix.md`
- `90_quality/non_functional_requirements.md`

### Step 7 — Sources handling
Place raw documents under `95_sources/` and maintain:
- `95_sources/index.md`
- `95_sources/links.md`

Rule: `95_sources/` is input material, not source of truth.

## Completion checklist
- [ ] Product framing is clear
- [ ] Open questions are tracked
- [ ] Requirements are traceable
- [ ] Current phase and tasks are defined
- [ ] Core architecture contracts exist
- [ ] First specs exist with acceptance criteria
- [ ] Verification commands and validation rows exist
