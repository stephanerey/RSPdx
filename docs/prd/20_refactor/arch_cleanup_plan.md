# Architecture Cleanup Plan for RSPdx

## Goal

This document expands upon the **Architecture Cleanup Checklist** provided in the PRD library.  It adapts the generic recommendations to the specifics of the RSPdx project.  The objective is to perform mechanical refactoring that improves the code structure and maintainability **without changing the user‑visible behaviour or degrading performance**.  The refactor will set the stage for future features such as additional demodulators and UI redesign by ensuring a clear separation of concerns.

## Checklist

- **Normalize imports**
  - Replace wildcard imports with explicit names and ensure that imports follow PEP 8 guidelines (standard library, third‑party libraries, then internal modules).
  - Adopt a consistent import style (absolute imports within the `rspdx` package instead of relative imports when appropriate) to avoid ambiguity.
  - Use type‐only imports guarded by `if TYPE_CHECKING:` to break circular dependencies when necessary.

- **Enforce module boundaries**
  - Establish clear boundaries between the **core**, **GUI**, **threading utilities**, **DSP**, and **demodulators** layers.  The core modules (`src/core/*`) must not import from the GUI; instead, they expose signals or callbacks consumed by the UI.
  - Introduce dedicated sub‑packages: `src/core/dsp/` for FFT, filtering, resampling and other signal processing functions, and `src/core/demodulators/` for each demodulation mode (`fm.py`, `am.py`, `ssb.py`, `cw.py`).
  - Move the provided `thread_manager.py` into `src/threading_utils/thread_manager.py` and adapt it to the project namespace.  Ensure that no part of the GUI imports PyQt threading classes directly; all background work goes through this manager.
  - Rename and adapt the `diagnostics_ui.py` module to `src/gui/threads_ui.py` and adjust imports to use our `ThreadManager` instead of the `antrack` package.  Likewise, relocate `log_viewer_ui.py` to `src/gui/log_viewer_ui.py` and replace `antrack.utils.paths` with a simple helper in `src/tools/paths.py`.
  - Decompose the monolithic `main_ui.py` by extracting each widget (e.g., spectrum view, waterfall view, receiver tab, configuration pane) into its own file under `src/gui/`.  This improves readability and simplifies testing.

- **Remove dead code**
  - Audit the `_archive/` directory and remove duplicate or obsolete files such as older copies of `sdr.py` and test scripts.  If any code is still needed for reference, copy relevant functions into documentation but ensure it does not run at startup.
  - Delete commented‑out sections and unused helper functions throughout the codebase.

- **Reduce cyclic dependencies**
  - Identify and break dependency cycles between `src/core/sdr.py`, `data_storage.py`, and GUI classes.  Where cycles are created by signal connections, use dependency inversion (define Qt signals in the core and connect them in the GUI).
  - Avoid high‑level modules importing lower‑level modules back and forth; instead, pass required objects via constructor parameters or use callbacks/signals.

- **Unify configuration and paths**
  - Centralise all configuration values (default sample rate, FFT size, gain settings, UI layout paths) in a new module, e.g. `src/config/settings.py`.  This file should be the only place where such constants are defined, making it easy to adjust or load them from a user‑editable file later.
  - Provide simple helper functions in `src/tools/paths.py` to return application directories (logs, configuration, recordings, etc.) similar to the existing `antrack.utils.paths` functions used by the imported UI widgets.
  - Ensure that logging is configured in one place, and that the log viewer reads from this unified log file.

## Acceptance criteria

- **Functionality preserved:** The refactored application must offer the same features and performance as the current code (spectral display, waterfall, existing demodulation, device discovery).  Any behavioural differences must be justified and documented.
- **Improved modularity:** The codebase should be reorganised into clearly defined packages (`core`, `gui`, `threading_utils`, `dsp`, `demodulators`, `tools`) with minimal coupling between them.
- **No dead code:** Obsolete files in `_archive/` should be removed or isolated such that they do not impact the build or runtime.
- **Configuration centralised:** Hard‑coded parameters are replaced with constants imported from `src/config/settings.py`.
- **Documentation:** Each new module and class includes English‑language docstrings and inline comments explaining non‑obvious logic.
- **Tests pass:** A minimal suite of smoke tests is added to ensure that the refactoring did not introduce regressions.  These tests should cover core DSP functions, thread management, and UI initialisation.

## Recommended steps

1. **Prepare new package structure.**  Create the new directories (`src/core/dsp`, `src/core/demodulators`, `src/threading_utils`, `src/tools`) and stub `__init__.py` files.  Move the uploaded `thread_manager.py` into `src/threading_utils/thread_manager.py` and update its imports to use PyQt5 from within this project.
2. **Integrate threading UI.**  Copy `diagnostics_ui.py` to `src/gui/threads_ui.py` and replace `from antrack.threading_utils.thread_manager import TaskStatus, ThreadManager` with `from rspdx.src.threading_utils.thread_manager import TaskStatus, ThreadManager`.  Similarly, copy `log_viewer_ui.py` into `src/gui/log_viewer_ui.py` and replace uses of `antrack.utils.paths` with helper functions in `src/tools/paths.py` (to be created).
3. **Refactor core modules.**  Identify logic in `sdr.py` and `data_storage.py` that belongs in signal processing and move it into functions inside `core/dsp`.  Extract each demodulation algorithm into its own file under `core/demodulators` and refactor `sdr.py` to dispatch to these functions.
4. **Decouple UI from core.**  Modify `main_ui.py` to use the `ThreadManager` for all long‑running tasks and to import demodulators via a registry or factory.  Create separate widget classes for each part of the interface and assemble them in `main_ui.py`.
5. **Eliminate dead code and cyclic imports.**  Remove the `_archive` folder or mark it as deprecated in the repository.  Review imports across modules and replace any remaining circular dependencies with signals, callbacks, or dependency injection.
6. **Centralise configuration and paths.**  Add a `settings.py` with all tunable constants and a `paths.py` module that returns directories for logs, recordings, and configuration.  Update all modules to import these rather than hard‑coding paths.
7. **Add tests and verify.**  Before and after refactoring, write smoke tests that instantiate the `ThreadManager`, perform a simple demodulation, and start the GUI without a device to ensure there are no runtime errors.  Use these tests to verify that the refactor has not introduced regressions.
