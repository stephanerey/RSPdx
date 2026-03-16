# Task Tracking Policy

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


## Files
- `02_tasks/tasks_now.md` is the live dashboard.
- `02_tasks/phases/Pxx_*.md` define the phase scope (canonical list).
- `02_tasks/snapshots/` stores immutable checkpoints (end of phase or major milestone).

## Rules
- During a phase, update **only** `tasks_now.md` daily.
- Phase scope (`phases/Pxx_*.md`) SHOULD be stable. If scope changes, record the decision in `01_product/decisions.md` and note the delta in the phase doc.
- At phase end: create a snapshot file and reset `tasks_now.md` for the next phase.

## Status values
Use: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `DROPPED`.

## Traceability
Each task MUST reference at least one PRD file (architecture / feature / quality) in the `PRD ref` column.
