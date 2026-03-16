# PRD Authoring Playbook (for the assistant / agent)

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Last updated:** 2026-02-12

## Purpose
This document defines the *methodology* to create or update a PRD using this template.
It is written for a human collaborator or a coding agent (Codex or not).

## Operating principles
- Prefer **explicit decisions** over implicit assumptions.
- If information is missing, make a **reasonable default**, mark it as `TODO`, and list it under `01_product/risks_and_assumptions.md` (Open questions).
- Keep documents **short and testable**. Split when a doc grows beyond ~2–3 pages.
- Every “deliverable” MUST have **verification steps**.

## Workflow (recommended)

### Step 0 — Initialize baseline
1. Ensure folder structure matches the template.
2. Read mandatory docs:
   - `PRD.md`
   - `00_conventions/conventions_and_naming.md`
   - `00_conventions/prd_structure_and_ids.md`
   - `00_conventions/task_tracking_policy.md`
   - `90_quality/definition_of_done.md`

### Step 1 — Product framing (source of truth)
Fill:
- `01_product/product_brief.md` (problem, personas, goals, non-goals, scope MVP vs V2+)
- `01_product/kpis.md` (what “success” means + how measured)
- `01_product/risks_and_assumptions.md` (assumptions, risks, open questions)
- `01_product/roadmap.md` (phases + milestones)

Rule: if a requirement is not in `01_product/`, it is not committed.

### Step 2 — Phase planning and tasks
1. Select the current phase `Pxx`.
2. Define the phase scope in `02_tasks/phases/Pxx_*.md`.
3. Populate `02_tasks/tasks_now.md` with actionable items.

Rules:
- `tasks_now.md` is the daily board.
- Phase scope docs SHOULD be stable; changes must be recorded in `01_product/decisions.md`.

### Step 3 — Architecture contract
Fill the minimal set (even if initially placeholders):
- `10_architecture/overview.md`
- `10_architecture/main_flows.md`
- `10_architecture/runtime_environment.md`
- `10_architecture/environments_and_deployment.md`
- `10_architecture/module_boundaries.md`
- `10_architecture/data_and_paths.md`

Add `data_schema.md` / `security_and_auth.md` when relevant.

### Step 4 — Feature and API specs
For each feature:
1. Create `30_feature/F###_<short_name>.md` using `feature_template.md`.
2. If it includes an API surface: create `30_feature/api/API###_<area>.md` (or keep in root `30_feature/` if you prefer).

Rules:
- Each spec MUST include Acceptance criteria + Testing notes.
- Specs MUST link to relevant architecture and quality docs.

### Step 5 — Quality gates
Fill:
- `90_quality/testing.md` (how to run tests)
- `90_quality/non_functional_requirements.md` (perf/reliability/security/observability)
- Optionally enforce `90_quality/quality_gate_checklist.md` in PR reviews.

### Step 6 — Sources handling (inputs)
Place raw documents under `95_sources/` and maintain:
- `95_sources/index.md` (annotated, with tags + “why it matters”)
- `95_sources/links.md` (URLs + short notes)

Rule: `95_sources/` is *not* the PRD truth; it is input material.

## Completion checklist (PRD ready to execute)
- [ ] `01_product/product_brief.md` has clear MVP scope + non-goals
- [ ] KPIs defined and measurable
- [ ] Risks/open questions listed
- [ ] Phase selected + tasks board populated
- [ ] Architecture overview + main flows are written
- [ ] First features have specs with acceptance criteria
- [ ] Verification commands exist (even if minimal)
