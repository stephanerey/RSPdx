# Conventions and Naming

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.

**Last updated:** 2026-03-12

## Language and RFC keywords
- PRD documents are written in **English** unless a project explicitly decides otherwise.
- Use RFC keywords: **MUST**, **SHOULD**, **MAY**.

## Document contract
Every spec-like document SHOULD include:
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
- Feature specs: `F###_<short_name>.md`
- API specs: `API###_<area>.md`
- Interface specs: `IFC###_<area>.md`
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
