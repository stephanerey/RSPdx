# Conventions and Naming

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Last updated:** 2026-03-07

## Language and RFC keywords
- PRD documents are written in **English**.
- Use RFC keywords: **MUST**, **SHOULD**, **MAY**.

## Document contract
Every spec document MUST include:
- **Goal**
- **Non-goals**
- **Constraints**
- **Acceptance criteria**
- **Testing notes**

## Traceability contract
- Requirements SHOULD have stable IDs.
- Features, interfaces, tasks, and validation rows MUST be linkable.
- A document is not actionable until it has a verification path.

## File naming
- Filenames: `snake_case.md`
- Project specs: `F###_<short_name>.md`, `API###_<area>.md`, `IFC###_<area>.md`
- ADRs: `ADR-###_<short_title>.md`

## ID families
- Requirements: `REQ-###`
- Features: `F###`
- APIs: `API###`
- Interface contracts: `IFC###`
- Tasks: `T-####`
- Product decisions: `D-###`
- Architecture decisions: `ADR-###`
- KPIs: `KPI-###`
- Validation rows: `VAL-###`

## Repo hygiene
- Keep docs short and testable.
- Prefer explicit constraints over implicit assumptions.
- Avoid hidden decisions.
- Product decisions go to `01_product/decisions.md`.
- Architecture decisions go to `10_architecture/adr/`.
- Open questions go to `01_product/open_questions.md`.
