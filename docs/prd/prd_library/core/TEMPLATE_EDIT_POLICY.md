# Template Edit Policy

## Purpose
This file defines which files are meant to stay stable in the project template and which files are meant to be filled or updated for each project.

## Rules
### LOCKED (template)
These files are library-controlled guidance and should generally not be edited inside a project PRD.
Examples:
- `README_FOR_HUMANS.md`
- `START_HERE.md`
- `00_conventions/*`
- `05_coding_agent/*`

### PROJECT (editable)
These files are meant to be filled or maintained for each project.
Examples:
- `PROJECT_INTAKE.md`
- `PROJECT_PROFILE.md`
- `PACKS_ACTIVE.md`
- `01_product/*`
- `02_tasks/*`
- `03_traceability/*`
- `04_requirements/*`
- `06_domain/*`
- `10_architecture/*`
- `20_refactor/*`
- `30_feature/*`
- `40_active_packs/*`
- `90_quality/*`
- `95_sources/*`
- `96_as_built/*`
- `97_gap_analysis/*`

## Important note
Imported packs inside `40_active_packs/` are project-local copies. They may be adapted locally if needed, but those adaptations must be reflected in `PACKS_ACTIVE.md`.
