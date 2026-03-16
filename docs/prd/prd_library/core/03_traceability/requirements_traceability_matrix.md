# Requirements traceability matrix

> **PRD Policy:** **PROJECT (editable)** — Link high‑level requirements to features, tasks, architecture and validation.  This matrix ensures that every requirement is implemented and verified.

**Last updated:** 2026‑03‑16

| Requirement ID | Description | Feature(s) / Component(s) | Tasks | Validation / test | Status |
|---|---|---|---|---|---|
| **REQ‑001 – Analog demodulation** | The system shall demodulate FM, AM, CW, USB and LSB signals with controllable bandwidth and gain. | Analog demodulator plugins; Pipeline manager; UI controls. | T‑0003, T‑0005, T‑0006 | Audio latency test (KPI‑01); CPU utilisation (KPI‑02); functional tests on synthetic signals. | Backlog |
| **REQ‑002 – Plugin architecture** | The system shall provide a plugin API to load/unload demodulators and analysis modules at runtime, with well‑defined life‑cycle functions. | Plugin manager; Plugin API; Example plugin. | T‑0003, T‑0004, T‑0007 | Plugin loads/unloads without crashing; API compliance unit tests; Integration test with example plugin. | Backlog |
| **REQ‑003 – Performance optimisation** | The system shall achieve audio latency ≤150 ms and CPU utilisation ≤50 % during analog demodulation. | DSP pipeline; C/C++ bindings; ThreadManager; UI rendering. | T‑0002, T‑0005, T‑0006, T‑0009 | Performance test harness measuring latency and CPU load; profiling reports. | Backlog |
| **REQ‑004 – Multi‑receiver UI** | The system shall support multiple simultaneous receivers with independent frequency/bandwidth settings and demodulator selection. | UI layer; Pipeline manager; ThreadManager. | T‑0003, T‑0006 | Manual test: create/destroy receivers; confirm correct audio outputs and visualisation; automated regression tests. | Backlog |
| **REQ‑005 – Cryptanalysis module** | The system shall provide a framework to plug in cryptanalysis modules that operate on demodulated or raw IQ data. | Plugin API; Cryptanalysis plugins. | T‑0008 | Unit tests for module loading; demonstration on synthetic hopping signals; security/privacy review. | Backlog |

**Status values:** `Backlog`, `In Progress`, `Review`, `Done`.

The matrix will be updated as new requirements are identified and tasks progress.  Each requirement must have at least one validation method defined.