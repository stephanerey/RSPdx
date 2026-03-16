# Roadmap

> **PRD Policy:** **PROJECT (editable)** — Define the development phases, timelines and milestones for this project.

**Last updated:** 2026‑03‑16

This roadmap outlines the major phases of the RSPdx project, from initial refactor to advanced features and hardening.  Phases are numbered (P00, P10, …) and correspond to milestones (M1–M5).  Dates are indicative and may be adjusted as the project evolves.

## Phases

| ID | Name | Description | Target completion |
|---|---|---|---|
| **P00** | Bootstrap | Set up the development environment, run the intake wizard, clone existing RSPdx code, and prepare the PRD and project profile. | 2026‑03‑20 |
| **P10** | Refactor | Integrate the ThreadManager from Antrack, restructure the code into modular components (device controller, pipeline manager, plugin manager, UI), and clean up legacy code. | 2026‑04‑15 |
| **P20** | Architecture definition | Specify the plugin API, define the data flow between components, design the module interfaces, and produce architecture diagrams and ADRs. | 2026‑04‑30 |
| **P30** | MVP analog | Implement analog demodulators (FM, AM, CW, USB, LSB) using C/C++ DSP libraries, build the multi‑receiver GUI, and deliver a functioning prototype with plugin skeleton. | 2026‑05‑31 |
| **P40** | Digital demod & plugins | Develop and integrate the first digital demodulator plugins (e.g. TETRA), enhance the plugin manager, and document the plugin SDK. | 2026‑07‑15 |
| **P50** | Cryptanalysis & extensions | Add cryptanalysis modules (e.g. hopping/frequency pattern analysis, symbol stream extraction), integrate external decoders if appropriate, and expose UI controls. | 2026‑09‑30 |
| **P60** | Optimisation & hardening | Profile and optimise performance, reduce latency and CPU usage, refine the UI, write comprehensive tests, package for distribution (PyInstaller, Docker), and ensure cross‑platform stability. | 2026‑11‑30 |

## Milestones

| Milestone | Definition | Target date |
|---|---|---|
| **M1 – Bootstrap complete** | Project environment ready, PRD drafted, codebase cloned and initial refactor tasks identified. | 2026‑03‑20 |
| **M2 – Refactor integrated** | ThreadManager integrated, modular code layout in place, and old code cleaned up. | 2026‑04‑15 |
| **M3 – MVP analog ready** | Analog demodulators operate with acceptable latency; multi‑receiver GUI works; plugin API skeleton loads a dummy plugin. | 2026‑05‑31 |
| **M4 – First digital plugin** | At least one digital demodulator plugin implemented and documented; plugin manager stable; UI supports plugin management. | 2026‑07‑15 |
| **M5 – Cryptanalysis demonstration** | Cryptanalysis module decodes or analyses a protected signal; performance meets KPIs; release candidate for V2. | 2026‑09‑30 |

## Notes

- Each phase may include one or more sprints.  Completion dates assume part‑time development and may slip depending on resource availability.
- The roadmap will be updated as the project progresses.  Major changes to scope or timing require a decision recorded in `decisions.md`.