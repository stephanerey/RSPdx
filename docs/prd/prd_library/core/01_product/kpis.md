# KPIs

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026‑03‑16

## KPI list

| KPI | Definition | How measured | Target | Notes |
|---|---|---|---|---|
| **KPI‑01 – Audio latency** | Time from IQ sample acquisition to audible audio output for analog modes. | Measured by injecting a known tone at a specific time into the signal chain and recording when it is heard via the audio output; use automated test harness. | ≤150 ms for FM/AM and ≤200 ms for CW/USB/LSB on mid‑range hardware. | Low latency is critical for real‑time reception and user experience. |
| **KPI‑02 – CPU utilisation** | Average CPU load while running one receiver with spectrum display and audio demodulation. | Sampled using OS‑level tools (e.g. `psutil` or perfmon) at 1 Hz during 5 minute test runs. | ≤50 % on a quad‑core Intel i5 or equivalent. | Includes DSP processing, UI rendering and plugin overhead. |
| **KPI‑03 – Supported modes count** | Number of fully functional demodulation modes delivered. | Count of analog modes and digital plugins available in the release. | 5 analog modes in MVP; +2 digital modes by V2+. | Demonstrates extensibility of the plugin framework. |
| **KPI‑04 – Crash‑free runtime** | Mean time between unhandled exceptions or crashes under continuous use. | Continuous 24‑hour stress testing with multiple receivers; log any unhandled exceptions. | Zero unhandled exceptions in 24 hours. | Robust error handling and thread management required. |
| **KPI‑05 – Plugin integration time** | Effort required to integrate a new digital demodulator module using the plugin API. | Measure the elapsed time for an experienced developer to create, build and register a new plugin from a template until it produces audio. | ≤2 working days including testing. | Indicates usability of the plugin SDK and documentation. |

## Measurement plan

- **Data sources:** Automated test harnesses (for latency), OS resource monitors (for CPU), release notes (for mode count), crash logs and telemetry (for runtime), and developer time tracking (for plugin integration).
- **Frequency:** KPIs are evaluated at the end of each development phase and before each public release.  Some KPIs (latency, CPU) may also be measured continuously during development to detect regressions early.
- **Owner:** Technical lead of the RSPdx project (e.g. Stéphane or delegated engineer) is responsible for ensuring metrics are collected and targets met.  KPI results are documented in the release notes and used to trigger corrective actions if necessary.