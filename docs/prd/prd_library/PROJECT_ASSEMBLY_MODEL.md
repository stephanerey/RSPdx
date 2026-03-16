# Project Assembly Model

## Goal
Create a project PRD that is autonomous enough to work locally, while preserving a clean master library upstream.

## Recommended workflow
1. Copy `core/` to a new project PRD workspace.
2. Run the intake wizard and point `--output-dir` to the project PRD root, or fill `PROJECT_INTAKE.md` and `PROJECT_PROFILE.md` manually.
3. Review the generated intake files and confirm pack suggestions.
4. Select packs.
5. Import the selected pack folders into `40_active_packs/` in the project PRD.
6. Fill `PACKS_ACTIVE.md` with:
   - pack name
   - version
   - source path in the library
   - imported files
   - local adaptations
7. Apply the pack guidance inside the core documents:
   - requirements in `04_requirements/`
   - architecture in `10_architecture/`
   - feature specs in `30_feature/`
   - quality and tests in `90_quality/`

## Why import packs into the project
This keeps the project portable and reviewable.
The project can be archived or shared without depending on the master library.

## What not to do
- Do not keep all packs in every project.
- Do not treat pack files as the only project truth.
- Do not fork the core structure inside each pack.

## Optional Codex bootstrap
- If the project will use Codex, instantiate `AGENTS.md`, `AGENTS.override.md`, and optionally `PLANS.md` from `tools/codex/templates/`.
- Keep repo rules in `AGENTS.md`, not hidden in chat prompts.
