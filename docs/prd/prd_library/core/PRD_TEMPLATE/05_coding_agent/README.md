# 05_coding_agent

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


## Purpose
Everything needed to run a coding agent (Codex or any other):
- base prompt (stable)
- phase prompts (scoped work)
- handoff templates
- execution plan template
- reusable snippets

## Typical usage
1) Ensure PRD baseline is filled (`PRD.md`, `00_conventions/*`, `01_product/*`).
2) Pick a phase prompt from `phases/` (or create one from `templates/`).
3) Provide the agent: base prompt + the phase prompt + relevant PRD links.
4) Maintain progress in `02_tasks/tasks_now.md`.
