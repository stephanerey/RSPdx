# Task Tracking Policy

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Last updated:** 2026-03-07

## Files
- `02_tasks/tasks_now.md` is the live dashboard.
- `02_tasks/phases/Pxx_*.md` define phase scope.
- `02_tasks/snapshots/` stores immutable checkpoints.

## Rules
- During a phase, update **only** `tasks_now.md` day-to-day.
- Phase scope docs SHOULD stay stable.
- If scope changes, record the product impact in `01_product/decisions.md` and the technical impact in `10_architecture/adr/` when relevant.
- At phase end: create a snapshot file and reset `tasks_now.md` for the next phase.

## Status values
Use: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `DROPPED`.

## Recommended task types
Use concise types such as: `feature`, `refactor`, `bug`, `doc`, `infra`, `research`, `test`.

## Traceability
Each task MUST reference at least one PRD file in the `PRD ref` column.
Each task SHOULD reference its target verification in the `Verification` column.
