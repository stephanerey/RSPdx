# PRD Ready Checklist

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Last updated:** 2026-02-12

Use this checklist to decide if the PRD is *actionable* (human or coding agent can execute with minimal back-and-forth).

## 1) Product framing (must be clear)
- [ ] `01_product/product_brief.md` has a clear **problem statement** and **target users/personas**
- [ ] **Goals** and **Non-goals** are explicit (no ambiguity)
- [ ] MVP scope is defined (what is included/excluded in **P30**)
- [ ] Key constraints are stated (platforms, budget, latency, privacy, etc.)

## 2) Success and risk management
- [ ] `01_product/kpis.md` defines measurable KPIs + how to measure them
- [ ] `01_product/risks_and_assumptions.md` lists assumptions, risks, and open questions
- [ ] Any scope change is recorded in `01_product/decisions.md` (if used)

## 3) Phases and tasks (execution-ready)
- [ ] Current phase is selected and scoped in `02_tasks/phases/Pxx_*.md`
- [ ] `02_tasks/tasks_now.md` contains the actionable work items for the current phase
- [ ] Each task references at least one PRD doc in the `PRD ref` column
- [ ] A snapshot plan exists (end of phase / milestones)

## 4) Architecture contract (minimum set exists)
- [ ] `10_architecture/overview.md` identifies components and responsibilities
- [ ] `10_architecture/main_flows.md` documents key end-to-end flows
- [ ] `10_architecture/runtime_environment.md` is reproducible (versions + toolchain)
- [ ] `10_architecture/environments_and_deployment.md` explains envs + deployment approach
- [ ] `10_architecture/module_boundaries.md` sets dependency rules
- [ ] `10_architecture/data_and_paths.md` defines path/data conventions
- [ ] `10_architecture/data_schema.md` exists if the project stores data (DB/files)

## 5) Feature/API specs (testable)
- [ ] Each planned feature has a spec `30_feature/F###_<name>.md`
- [ ] Feature specs include: Goal, Non-goals, Constraints, Acceptance criteria, Testing notes
- [ ] Each API surface has an `API###` spec with request/response examples and error codes
- [ ] Specs link to relevant architecture and quality docs

## 6) Quality gates (no surprises)
- [ ] `90_quality/definition_of_done.md` is accepted and used
- [ ] `90_quality/testing.md` includes actual commands (or clearly states TBD)
- [ ] `90_quality/non_functional_requirements.md` covers relevant NFRs
- [ ] `90_quality/quality_gate_checklist.md` is enabled if you want strict gating

## 7) Sources are cleanly separated
- [ ] Raw inputs are stored under `95_sources/`
- [ ] `95_sources/index.md` is maintained (annotated: why it matters + tags)
- [ ] No “source of truth” decisions are hidden inside `95_sources/`

## 8) Agent readiness (if using an agent)
- [ ] `05_coding_agent/prd_authoring_playbook.md` is present and followed
- [ ] `05_coding_agent/base_prompt.md` references the current phase prompt
- [ ] (Optional) `05_coding_agent/handoffs/` is filled for faster ramp-up

## Result
- If **all sections 1–6** are checked → PRD is executable.
- If not → list missing items in `02_tasks/tasks_now.md` as bootstrap tasks.
