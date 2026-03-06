# UI Modularization (Optional)

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


## Goal
Define how UI is split into modules/components and how logic is separated.

## Rules
- UI widgets/components stay in UI layer.
- Business logic is not embedded in UI event handlers.
- Async/threading boundaries are explicit.

## Acceptance criteria
- UI remains responsive under load.
