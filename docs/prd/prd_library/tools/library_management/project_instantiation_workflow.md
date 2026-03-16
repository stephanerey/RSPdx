# Project Instantiation Workflow

## Goal
Turn the master library into a project-specific PRD.

## Recommended steps
1. Copy `core/` into a new project PRD folder.
2. Either fill `PROJECT_PROFILE.md` and `PROJECT_INTAKE.md` manually, or run `tools/project_intake_wizard/wizard.py`.
3. Review the generated `PROJECT_INTAKE.md`, `PROJECT_PROFILE.md`, and `PACKS_ACTIVE.md`.
4. Select packs using `packs/PACK_SELECTION_GUIDE.md`.
5. Copy selected packs into the project under `40_active_packs/`.
6. Register them in `PACKS_ACTIVE.md`.
7. Apply pack impacts into the core docs.
8. Start project-specific feature specs and tasks.

## Output expectations
The resulting project PRD should contain:
- one generic backbone
- one compact intake layer
- only the selected packs
- a clear pack manifest
- no hidden dependencies on the master library for day-to-day use

## Optional Codex bootstrap
- If the project will use Codex, instantiate `AGENTS.md`, `AGENTS.override.md`, and optionally `PLANS.md` from `tools/codex/templates/`.
- Keep repo rules in `AGENTS.md`, not hidden in chat prompts.
