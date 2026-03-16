# Conventions and Naming

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


## Language & RFC keywords
- PRD documents are written in **English**.
- Use RFC keywords: **MUST**, **SHOULD**, **MAY**.

## Document contract
Every spec document MUST include:
- **Goal**
- **Non-goals**
- **Constraints**
- **Acceptance criteria**
- **Testing notes** (how to verify)

## Naming
- Filenames: `snake_case.md`
- Feature IDs: `F###` (e.g. `F012`)
- API IDs: `API###` (e.g. `API004`)
- Task IDs: `T-####` (e.g. `T-0301`)
- Phases: `P00`, `P10`, `P30`, …

## Repo hygiene (general)
- Keep docs short and testable.
- Prefer explicit constraints over implicit assumptions.
- Avoid hidden decisions: record them in `01_product/decisions.md`.
