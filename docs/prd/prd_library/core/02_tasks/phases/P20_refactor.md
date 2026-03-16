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
| **T‑0101** | Set up new package structure & integrate thread manager | DONE | refactor | 20_refactor/arch_cleanup_plan.md | Directory structure created; thread manager runs without import errors. | `src/threading_utils/thread_manager.py` is now the primary implementation, with compatibility kept under `src/threading/`. |
| **T‑0102** | Port diagnostics and log viewer UIs | DONE | refactor | 20_refactor/arch_cleanup_plan.md | Threads UI and log viewer display correct information via the new `ThreadManager`. | `src/gui/threads_ui.py` and `src/gui/log_viewer_ui.py` are integrated as docks in the main window. |
| **T‑0103** | Extract DSP and demodulator functions | DONE | refactor | 20_refactor/arch_cleanup_plan.md | Demodulator modules exist (`am.py`, `fm.py`, `ssb.py`, `cw.py`); DSP routines placed in `core/dsp`. | `Receiver` and `SDRController` now use shared DSP helpers; runtime mode selection is available in the receiver UI. |
| **T‑0104** | Decouple UI and modularise widgets | DONE | refactor | 20_refactor/arch_cleanup_plan.md | UI widgets separated; no cyclic imports; plugin manager skeleton in place. | `main_ui.py` now delegates monitoring, display, and receiver runtime responsibilities to dedicated GUI controller modules. |
| **T‑0105** | Remove dead code and normalise imports | DONE | refactor | 20_refactor/arch_cleanup_plan.md | `_archive` removed or archived; imports follow guidelines. | Legacy source files were deleted from `_archive/`; remaining folder content is marked deprecated and excluded from runtime use. |
| **T‑0106** | Centralise configuration and paths | DONE | refactor | 20_refactor/arch_cleanup_plan.md | `settings.py` and `paths.py` created; constants removed from code. | Logging now uses the same runtime path helpers as the log viewer. |
| **T‑0107** | Add smoke tests and perform regression | DONE | test | 20_refactor/arch_cleanup_plan.md | Test suite passes on baseline and refactored code; no performance regression. | `tests/test_refactor_smoke.py` executed successfully in the project `.venv`; full hardware/performance validation remains to be completed on target SDR setups. |
