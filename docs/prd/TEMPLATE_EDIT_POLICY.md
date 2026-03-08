# Template Edit Policy

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Last updated:** 2026-03-07

## Purpose
Make it explicit which files are template-stable and which files are expected to change in a project.

## File classes
- **LOCKED (template)**: stable cross-project template content
- **PROJECT (editable)**: expected to be filled for each project
- **OPTIONAL (project)**: create/fill only when relevant

## Rules
- A project PRD MUST NOT edit files marked **LOCKED (template)**.
- If a project needs a variant of a LOCKED file, create a new project file and reference it from `PRD.md`.
- Template changes SHOULD happen in the template source, then be propagated intentionally.
- Agents MUST read the file header before modifying a document.

## Default classification by area
| Path | Class | Notes |
|---|---|---|
| `START_HERE.md` | LOCKED | Entry point |
| `PRD_READY_CHECKLIST.md` | LOCKED | Readiness gate |
| `00_conventions/*` | LOCKED | Stable rules |
| `01_product/*` | PROJECT | Project truth |
| `02_tasks/*` | PROJECT | Daily execution |
| `03_traceability/*` | PROJECT | Living matrix |
| `05_coding_agent/*` | LOCKED | Stable prompts and templates |
| `10_architecture/adr/ADR-000_template.md` | LOCKED | Copy to create ADRs |
| `10_architecture/*` | PROJECT | Technical truth |
| `20_refactor/*` | Mostly LOCKED | Copy templates into project docs as needed |
| `30_feature/*_template.md` | LOCKED | Copy to create specs |
| `30_feature/F###_*.md` | PROJECT | Project specs |
| `30_feature/API###_*.md` | PROJECT | Project API specs |
| `30_feature/IFC###_*.md` | PROJECT | Project interface specs |
| `90_quality/definition_of_done.md` | LOCKED by default | Copy if project needs stricter variant |
| `90_quality/*` other than DoD/checklists | PROJECT | Quality truth |
| `95_sources/*` | PROJECT | Input material |

## How to create project-specific specs from templates
- Copy `30_feature/feature_template.md` to `30_feature/F###_<short_name>.md`
- Copy `30_feature/api_spec_template.md` to `30_feature/API###_<area>.md`
- Copy `30_feature/interface_contract_template.md` to `30_feature/IFC###_<area>.md`
- Copy `10_architecture/adr/ADR-000_template.md` to `10_architecture/adr/ADR-###_<title>.md`
