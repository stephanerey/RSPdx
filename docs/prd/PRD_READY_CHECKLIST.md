# PRD Ready Checklist

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Last updated:** 2026-03-07

Use this checklist to decide if the PRD is *actionable* (human or coding agent can execute with minimal back-and-forth).

## 1) Product framing (must be clear)
- [ ] `01_product/product_brief.md` has a clear **problem statement** and **target users/personas**
- [ ] **Goals** and **Non-goals** are explicit
- [ ] MVP scope is defined (what is included/excluded in **P30**)
- [ ] Key constraints are stated (platforms, budget, latency, privacy, etc.)
- [ ] Open questions are tracked in `01_product/open_questions.md`

## 2) Success and risk management
- [ ] `01_product/kpis.md` defines measurable KPIs + how to measure them
- [ ] `01_product/risks_and_assumptions.md` lists assumptions and risks
- [ ] Product-level scope changes are recorded in `01_product/decisions.md`

## 3) Traceability (must exist)
- [ ] `03_traceability/requirements_traceability_matrix.md` exists and is maintained
- [ ] Core requirements have IDs (`REQ-###`) or equivalent tracked rows
- [ ] Each MVP feature maps to tasks and verification
- [ ] No important requirement is “doc-only” without implementation or test path

## 4) Phases and tasks (execution-ready)
- [ ] Current phase is selected and scoped in `02_tasks/phases/Pxx_*.md`
- [ ] `02_tasks/tasks_now.md` contains the actionable work items for the current phase
- [ ] Each task references at least one PRD doc in the `PRD ref` column
- [ ] Each task has a verification note or target validation row
- [ ] A snapshot plan exists (end of phase / milestones)

## 5) Architecture contract (minimum set exists)
- [ ] `10_architecture/overview.md` identifies components and responsibilities
- [ ] `10_architecture/main_flows.md` documents key end-to-end flows
- [ ] `10_architecture/runtime_environment.md` is reproducible (versions + toolchain)
- [ ] `10_architecture/package_layout.md` removes file-placement ambiguity
- [ ] `10_architecture/module_boundaries.md` sets dependency rules
- [ ] `10_architecture/configuration_strategy.md` defines config sources and precedence
- [ ] `10_architecture/external_dependencies.md` identifies critical third-party pieces
- [ ] `10_architecture/versioning_and_release_policy.md` defines release and compatibility rules
- [ ] Architecture decisions are recorded under `10_architecture/adr/`

## 6) Feature/API/interface specs (testable)
- [ ] Each planned feature has a spec `30_feature/F###_<name>.md`
- [ ] Feature specs include: Goal, Non-goals, Constraints, Acceptance criteria, Testing notes
- [ ] Each HTTP/API surface has an `API###` spec when relevant
- [ ] Each non-HTTP interface has an `IFC###` contract when relevant
- [ ] Specs link to relevant architecture and quality docs

## 7) Quality gates (no surprises)
- [ ] `90_quality/definition_of_done.md` is accepted and used
- [ ] `90_quality/testing.md` includes actual commands or clearly scoped TBDs
- [ ] `90_quality/validation_matrix.md` maps verification to requirements/features
- [ ] `90_quality/non_functional_requirements.md` covers relevant NFRs

## 8) Sources are cleanly separated
- [ ] Raw inputs are stored under `95_sources/`
- [ ] `95_sources/index.md` is maintained (annotated: why it matters + tags)
- [ ] No “source of truth” decisions are hidden inside `95_sources/`

## 9) Agent readiness (if using an agent)
- [ ] `05_coding_agent/prd_authoring_playbook.md` is present and followed
- [ ] `05_coding_agent/base_prompt.md` references the stable rules and current phase prompt
- [ ] The edit policy is understood (`TEMPLATE_EDIT_POLICY.md`)
- [ ] (Optional) `05_coding_agent/handoffs/` is filled for faster ramp-up

## Result
- If sections **1–7** are checked → PRD is executable.
- If not → list missing items in `02_tasks/tasks_now.md` as bootstrap tasks.
