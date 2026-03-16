# Current tasks

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
| **T‑0001** | Done | Prepare and populate the PRD based on the enhanced template.  Copy the editable files from the core template and fill in the product brief, KPIs, roadmap, decisions, risk register, open questions, and architecture overview. | Assistant | M | 2026‑03‑16 | All listed PRD files exist in `docs/prd/prd_library/core` and contain the agreed content. |
| **T‑0002** | To‑Do | Integrate the ThreadManager from the Antrack project into the RSPdx codebase; update the build system and UI to include `threadmanager.ui`. | Dev lead | H | 2026‑04‑15 | ThreadManager runs within RSPdx; UI shows thread stats; tasks and loops managed via ThreadManager. |
| **T‑0003** | Backlog | Refactor the current code into modular components: device controller, pipeline manager, plugin manager, UI layer and data storage.  Remove monolithic dependencies. | Dev team | H | 2026‑04‑30 | Modules compiled, minimal couplings; architecture diagram updated; existing features still functional. |
| **T‑0004** | Backlog | Define the plugin API: data structures, life‑cycle functions, build system integration and versioning.  Provide a sample skeleton plugin. | Architecture lead | M | 2026‑04‑30 | API specification document approved; example plugin builds and loads successfully. |
| **T‑0005** | Backlog | Implement analog demodulation modes (FM, AM, CW, USB, LSB) using appropriate C/C++ libraries.  Expose controls in the GUI. | DSP engineer | H | 2026‑05‑31 | Each mode demodulates test signals correctly with acceptable latency; KPIs met. |
| **T‑0006** | Backlog | Develop the multi‑receiver GUI: add/remove receivers, frequency/bandwidth controls, spectrum/waterfall plots, demodulator selection, plugin management panel. | UI/UX developer | H | 2026‑05‑31 | GUI demonstrates responsive controls; user can operate multiple receivers concurrently; no UI thread blocking. |
| **T‑0007** | Backlog | Implement the first digital demodulator plugin (e.g. TETRA) using the plugin API.  Document build and integration steps. | DSP engineer | M | 2026‑07‑15 | Digital plugin decodes test TETRA signals; plugin manager handles dynamic loading/unloading; CPU usage acceptable. |
| **T‑0008** | Backlog | Add basic cryptanalysis module to analyse frequency hopping patterns and symbol statistics. | Researcher | M | 2026‑09‑30 | Module analyses synthetic hopping signals and produces visual/ textual output. |
| **T‑0009** | Backlog | Perform performance profiling and optimisation: identify bottlenecks in DSP pipeline, multi‑threading and UI; implement improvements (vectorisation, parallelism). | Perf engineer | H | 2026‑11‑30 | KPI‑01/02 targets met on reference hardware; profiling report and optimisation commits. |

## Done (recent)

| ID | Description | Completed on |
|---|---|---|
| **T‑0001** | Populated the PRD based on the enhanced template with detailed content tailored to RSPdx. | 2026‑03‑16 |
