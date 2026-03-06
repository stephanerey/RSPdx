# 02_tasks

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


## Purpose
Phase-aware task management: current execution board + per-phase scope + immutable snapshots.

## Files
- `tasks_now.md`: live execution board
- `phases/`: phase scopes (canonical lists)
- `snapshots/`: immutable checkpoints

## Workflow
1) Start a phase: create/update `phases/Pxx_*.md`
2) Drive daily work via `tasks_now.md`
3) Snapshot at milestones or end of phase, then reset `tasks_now.md`
