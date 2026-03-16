# PRD Library — Human Guide (EN)

This library is used to build project PRDs in a way that stays consistent, reusable, and usable by both humans and coding agents.

## Core idea
The system is built around three blocks:
- a stable generic **core**
- specialized **packs** activated only when relevant
- **tools** for intake, assembly, Codex, skills, and library governance

The repository is organized so that a human first sees the onboarding documents, while the actual machinery lives under `prd_library/`.

## Where to start
Read in this order:
1. `START_HERE.md`
2. `QUICKSTART.md`
3. `run_wizard.py` or `prd_library/tools/project_intake_wizard/README.md`
4. `prd_library/README.md`
5. `prd_library/LIBRARY_STRUCTURE.md`
6. `prd_library/PROJECT_ASSEMBLY_MODEL.md`

## If you do not know what to fill in yet
You do not need to understand the full PRD to get started.
The easiest path is to use the intake wizard.

The wizard can either:
- ask guided questions
- parse a structured markdown brief

It then generates:
- `PROJECT_INTAKE.md`
- `PROJECT_PROFILE.md`
- `PACKS_ACTIVE.md`
- `NEXT_STEPS_FOR_GPT.md`

These files provide a clean starting point before asking GPT to complete the PRD.

## Role of the internal top-level folders
- `prd_library/core/` — generic PRD backbone
- `prd_library/packs/` — specialized overlays by project family
- `prd_library/tools/` — workflow method, wizard, governance, Codex, skills
- `prd_library/examples/` — examples and future reference cases

## Important rule
The PRD remains the project truth.
Packs complement it.
Prompts accelerate it.
Skills assist it.
None of them should become a hidden second source of truth.

## Why this library exists
It is designed to avoid three common failures:
- specs scattered across chats
- poorly framed projects at startup
- coding agents that get the technical implementation right but miss the business logic

That is also why the core includes a `06_domain/` layer for projects with strong operational logic.

## If you use Codex
The repository also includes a minimal bootstrap kit in `prd_library/tools/codex/templates/` to instantiate quickly:
- `AGENTS.md`
- `AGENTS.override.md`
- `PLANS.md`

This helps avoid starting the repo/Codex integration from scratch.
