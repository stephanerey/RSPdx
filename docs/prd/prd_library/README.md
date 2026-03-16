# prd_library

Internal library contents for the PRD system.
The human-facing entry documents are now located at the repository root.

Master library for building project PRDs from a stable generic core plus specialized packs.

For human-oriented onboarding, start from the repository root: `README.md`, `README_FR.md`, `README_EN.md`, and `START_HERE.md`.
If you want a guided entry point instead of filling the PRD manually, use `../run_wizard.py` from the repository root or read `tools/project_intake_wizard/README.md`.

This library is meant to serve three audiences:
- humans who need a reusable and understandable PRD system
- coding agents that need a predictable document structure
- future tooling that will assemble project PRDs automatically from the core and selected packs

## Design principles
- The **core** stays generic and durable.
- **Packs** stay modular and domain-specific.
- **Tools** support instantiation, intake, maintenance, and future Codex skill integration.
- A generated project PRD should be mostly autonomous once assembled.

## Top-level structure
- `core/` — universal PRD template shared by all projects
- `packs/` — specialized overlays by project family
- `tools/` — library management, intake, and future Codex skill assets
- `examples/` — optional example compositions and future samples

## Recommended usage model
1. Keep this library as the master source.
2. Start a new project from `core/`.
3. Optionally run the intake wizard from `tools/project_intake_wizard/`.
4. Select one or more packs from `packs/`.
5. Import only the packs that apply to the project.
6. Record activation and imported files in `core/PACKS_ACTIVE.md` inside the instantiated project.
7. Keep project truth in the core PRD documents, not hidden inside pack notes.
8. If the project will use Codex, instantiate the starter files from `tools/codex/templates/`.

## Output philosophy
This library is not just a template dump.
It is a composition system:
- **core** provides the backbone
- **packs** provide specialized constraints and guidance
- **tools** explain how to assemble and maintain the whole thing cleanly
