# QUICKSTART

## Goal
Create the first usable PRD skeleton for a new project without reading the whole library first.

## Fast path
1. Copy `prd_library/core/` to your project PRD workspace.
2. Run the wizard from the repository root and point `--output-dir` to that project PRD root.
3. Review the generated `PROJECT_INTAKE.md`, `PROJECT_PROFILE.md`, and `PACKS_ACTIVE.md`.
4. Copy only the relevant packs from `prd_library/packs/` into `40_active_packs/`.
5. Ask GPT to read the generated intake files and prefill the PRD.
6. If the project will use Codex, instantiate `AGENTS.md` and related Codex templates from `prd_library/tools/codex/templates/`.
7. Only after that, use Codex for targeted implementation slices.

## Root launcher
Interactive mode:
```bash
python run_wizard.py --mode interactive --output-dir /path/to/generated_intake
```

Structured brief mode:
```bash
python run_wizard.py --mode brief --input-file /path/to/brief.md --output-dir /path/to/generated_intake
```

## Internal paths you will most often need
- `prd_library/core/`
- `prd_library/packs/`
- `prd_library/tools/project_intake_wizard/`
- `prd_library/tools/codex/`
