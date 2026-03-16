# P20 Refactor – Phase Scope

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

## Objective

Implement the architecture cleanup and modular refactor for RSPdx to establish a maintainable, extensible codebase while preserving existing functionality and performance.  This phase lays the groundwork for future features by separating the UI from the core logic, introducing dedicated packages for DSP and demodulation, integrating a thread manager for background tasks, and centralising configuration.

## Entry criteria

- The project intake and architecture cleanup plan (`20_refactor/arch_cleanup_plan.md`) are approved.
- A baseline build of RSPdx runs on both Windows and Linux using the existing monolithic code.
- External dependencies (`SoapySDR` and the SDRplay API) are installed on target machines.
- Source files `thread_manager.py`, `diagnostics_ui.py` and `log_viewer_ui.py` from the Antrack project are available in the repository.

## Exit criteria

- All tasks T‑0101 through T‑0107 in `02_tasks/tasks_now.md` are marked as **Done**.
- The new package structure (`core`, `core/dsp`, `core/demodulators`, `threading_utils`, `tools`, `config`) exists and the application imports successfully from these packages.
- Signal‑processing routines and demodulators are isolated in their respective sub‑packages and invoked from the core without circular dependencies.
- The GUI is modularised into separate widgets under `gui/` and communicates with the core via signals or callbacks; no GUI module imports from `core` are cyclical.
- The `_archive/` folder and any dead code are removed; imports follow PEP 8 guidelines; configuration values are centralised in `config/settings.py` and paths in `tools/paths.py`.
- A minimal smoke test suite passes on the refactored codebase; measured performance (CPU usage, latency) is not degraded relative to the baseline.
- Architecture diagrams and the PRD are updated to reflect the new structure and decisions (e.g. choice to retain SoapySDR for future SDR support).

## Tasks

| ID | Title | Status | Type | PRD ref | Verification | Notes |
|---|---|---|---|---|---|---|
| **T‑0101** | Set up new package structure & integrate thread manager | TODO | refactor | 20_refactor/arch_cleanup_plan.md | Directory structure created; thread manager runs without import errors. |  |
| **T‑0102** | Port diagnostics and log viewer UIs | TODO | refactor | 20_refactor/arch_cleanup_plan.md | Threads UI and log viewer display correct information via the new `ThreadManager`. | Rename `diagnostics_ui.py` → `threads_ui.py`. |
| **T‑0103** | Extract DSP and demodulator functions | TODO | refactor | 20_refactor/arch_cleanup_plan.md | Demodulator modules exist (`am.py`, `fm.py`, `ssb.py`, `cw.py`); DSP routines placed in `core/dsp`. |  |
| **T‑0104** | Decouple UI and modularise widgets | TODO | refactor | 20_refactor/arch_cleanup_plan.md | UI widgets separated; no cyclic imports; plugin manager skeleton in place. |  |
| **T‑0105** | Remove dead code and normalise imports | TODO | refactor | 20_refactor/arch_cleanup_plan.md | `_archive` removed; imports follow guidelines. |  |
| **T‑0106** | Centralise configuration and paths | TODO | refactor | 20_refactor/arch_cleanup_plan.md | `settings.py` and `paths.py` created; constants removed from code. |  |
| **T‑0107** | Add smoke tests and perform regression | TODO | test | 20_refactor/arch_cleanup_plan.md | Test suite passes on baseline and refactored code; no performance regression. |  |
