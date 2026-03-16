# PRD

> **PRD Policy:** **PROJECT (editable)** — This is the top‑level project PRD index for RSPdx.

## Purpose
This file is the entry point for the product requirements document. It explains where to start reading and how the PRD is structured for the RSPdx project.  The PRD serves as the single source of truth for functional and technical decisions, tasks, and quality criteria.  Every change to the product must be reflected here or in a linked document.

## Project composition
The PRD is organized around a **core template** that has been customized for RSPdx and a set of editable sections for this project.  The folder structure mirrors the original template, and each file is clearly marked as either **PROJECT (editable)** or **LOCKED (template)**.  The editable files capture our specific decisions, requirements and tasks, while the locked files preserve generic guidance.

Core components:
- **Core PRD template:** this folder (`docs/prd/prd_library/core`) contains all PRD content.  Editable files are marked accordingly.
- **Initial intake layer:** `PROJECT_INTAKE.md` describes the problem space, scope and high‑level requirements captured during the project intake.
- **Project profile:** `PROJECT_PROFILE.md` records the domain, intensity and pack selections for RSPdx.
- **Active pack manifest:** `PACKS_ACTIVE.md` lists any optional PRD packs that augment the core template.

## Read first
1. `README_FOR_HUMANS.md` — overview of how to use this PRD
2. `PROJECT_INTAKE.md` — high‑level problem definition and context
3. `PROJECT_PROFILE.md` — project family, domain intensity and pack selections
4. `PACKS_ACTIVE.md` — active optional packs (if any)
5. `01_product/product_brief.md` — our product brief, personas, goals and constraints
6. `04_requirements/requirements_catalog.md` — catalogue of detailed requirements (future)
7. `10_architecture/overview.md` — high‑level architecture and flows
8. `02_tasks/tasks_now.md` — current task board and backlog
9. `90_quality/validation_matrix.md` — how we prove that requirements are met

## Core folders
The core folders mirror the original template:

- `00_conventions/` — naming conventions, file locking policies and templates
- `01_product/` — product brief, KPIs, roadmap, decisions, risks, open questions
- `02_tasks/` — current tasks and backlog
- `03_traceability/` — requirements traceability matrix
- `04_requirements/` — catalogue of atomic requirements (to be populated)
- `05_coding_agent/` — guidance for the coding agent (not yet used)
- `06_domain/` — domain‑specific context (not used for RSPdx)
- `10_architecture/` — architecture overview, main flows, runtime environment, configuration, dependencies, versioning, logging
- `20_refactor/` — refactor guides and documentation of changes from the original code
- `30_feature/` — feature specifications and interface contracts
- `40_active_packs/` — overlays from optional packs (none active)
- `90_quality/` — non‑functional requirements, testing plan, validation matrix
- `95_sources/` — citations and sources for decisions and requirements
- `96_as_built/` — documentation of the implemented system (to be updated post‑implementation)
- `97_gap_analysis/` — analysis of gaps between spec and implementation (future)

Each editable file will be updated as decisions are made and tasks are completed.  Locked files remain unchanged and serve as reference.