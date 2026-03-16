# Current tasks (Refactor Phase)

> **PRD Policy:** **PROJECT (editable)** — Maintain the task board for the current phase.  Each task should be linked to requirements, features, or refactor items.

**Legend:**

| Status | Meaning |
|---|---|
| **Backlog** | Task identified but not yet prioritised or scheduled. |
| **To‑Do** | Task scheduled for the current or next sprint but not yet started. |
| **In Progress** | Work on this task has begun. |
| **Review** | Implementation complete; awaiting code review or testing. |
| **Done** | Task verified as complete and meeting acceptance criteria. |

## Active tasks

| ID | Status | Description | Owner | Difficulty | Due | Verification |
|---|---|---|---|---|---|---|
| **T‑0101** | Done | **Set up the new package structure and integrate the thread manager.** Create sub‑packages `core/dsp`, `core/demodulators`, `threading_utils`, and `tools`, add `__init__.py` files, move `thread_manager.py` into `threading_utils/thread_manager.py` and adapt imports. | Dev lead | M | 2026‑03‑31 | New directories exist; `ThreadManager` runs within RSPdx and no import errors occur. |
| **T‑0102** | Done | **Port and adapt the diagnostics and log viewer UIs.** Copy `diagnostics_ui.py` to `gui/threads_ui.py` and `log_viewer_ui.py` to `gui/log_viewer_ui.py`, update imports to use the local `ThreadManager` and new path helpers, and ensure the UIs display thread stats and log output. | UI developer | M | 2026‑04‑07 | New UI components load without errors and correctly show thread statuses and log messages. |
| **T‑0103** | Done | **Extract DSP and demodulation functions.** Move FFT, filtering, decimation and resampling routines into `core/dsp/`; create demodulator modules `am.py`, `fm.py`, `ssb.py` (including USB/LSB) and `cw.py` under `core/demodulators/`; refactor the core to call these modules. | DSP engineer | H | 2026‑04‑21 | Each demodulator module demodulates sample signals correctly; DSP functions are encapsulated and imported from `core/dsp`. |
| **T‑0104** | Done | **Decouple the UI from the core and modularise the interface.** Refactor `main_ui.py` by splitting each widget (spectrum view, waterfall view, receiver tab, config pane) into separate files under `gui/`; connect to the core via signals/callbacks; incorporate the plugin manager skeleton. | Dev team | H | 2026‑05‑05 | UI modules import core only via signals; application runs without circular dependencies; existing features operate as before. |
| **T‑0105** | Done | **Remove dead code and obsolete files.** Clean the `_archive/` folder, delete unused scripts and duplicate modules, and normalise imports (PEP 8 ordering, explicit names). | Dev lead | L | 2026‑04‑15 | `_archive` source files removed or isolated; no unused code reachable at runtime; import statements follow the guidelines. |
| **T‑0106** | Done | **Centralise configuration and paths.** Create `config/settings.py` to store default parameters (sample rate, FFT size, gains); implement `tools/paths.py` to provide application directories (logs, recordings, etc.); update modules to import from these. | Dev team | M | 2026‑04‑30 | Configuration values are no longer hard‑coded; paths are obtained via helper functions; application still runs correctly. |
| **T‑0107** | Done | **Add smoke tests and run regression.** Write a minimal test suite that instantiates `ThreadManager`, performs basic DSP operations, and launches the GUI without hardware; run tests before and after refactoring to verify no regressions. | Test engineer | M | 2026‑05‑15 | Test suite passes on both the baseline and refactored code; CI pipeline green. |

## Done (recent)

| ID | Description | Completed on |
|---|---|---|
| **T‑0101** | New package structure created; `ThreadManager` moved under `src/threading_utils` with compatibility wrapper retained under `src/threading`. | 2026‑03‑16 |
| **T‑0102** | `src/gui/threads_ui.py` and `src/gui/log_viewer_ui.py` added and integrated into the main window. | 2026‑03‑16 |
| **T‑0103** | DSP helpers split into dedicated modules and demodulator modules added for AM/SSB/CW alongside FM. | 2026‑03‑16 |
| **T‑0104** | Main window responsibilities split across dedicated GUI controllers for monitoring, display, and receiver runtime coordination. | 2026‑03‑16 |
| **T‑0105** | Legacy source files removed from `_archive/`; remaining directory explicitly marked as deprecated/non-runtime. | 2026‑03‑16 |
| **T‑0106** | Central settings expanded and `src/tools/paths.py` introduced for runtime directories and logs. | 2026‑03‑16 |
| **T‑0107** | Smoke tests added under `tests/test_refactor_smoke.py` and executed in the project `.venv`. | 2026‑03‑16 |
