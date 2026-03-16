# Thread Manager Spec (Optional)

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


## Goal
Define requirements for a thread/task manager (GUI apps, background work).

## Required capabilities
- Task lifecycle: start/stop/cancel
- Progress reporting
- Error capture and surfacing
- Graceful shutdown
- Ownership/registry

## Acceptance criteria
- No orphan threads/tasks on shutdown.
- Exceptions are visible and logged.
