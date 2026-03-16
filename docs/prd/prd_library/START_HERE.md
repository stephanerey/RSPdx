# START HERE

This file explains how to use the PRD library itself.

## Read in this order
1. `../README.md`
2. `../README_FR.md` or `../README_EN.md`
3. `../QUICKSTART.md`
4. `README.md`
5. `LIBRARY_STRUCTURE.md`
6. `PROJECT_ASSEMBLY_MODEL.md`
7. `tools/project_intake_wizard/README.md`
8. `packs/PACK_STANDARD.md`
9. `tools/library_management/project_instantiation_workflow.md`
10. `tools/codex/CODEX_OPERATING_MODEL.md`
11. `tools/README.md`

## Short path
- Copy `core/` into the new project PRD workspace.
- If the human wants a guided start, run `../run_wizard.py` from the repository root and point `--output-dir` to the project PRD root.
- Review the generated `PROJECT_INTAKE.md`, `PROJECT_PROFILE.md`, and `PACKS_ACTIVE.md`.
- Select packs from `packs/`.
- Import the selected pack folders into the project under `40_active_packs/`.
- Record what was imported in `PACKS_ACTIVE.md`.
- Reflect the pack guidance into the core documents.

## Important rule
Packs complement the core; they do not replace it.
