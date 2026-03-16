# Validation matrix

> **PRD Policy:** **PROJECT (editable)** — Define how each requirement and non‑functional requirement will be validated.  This matrix ensures that no requirement is left untested.

**Last updated:** 2026‑03‑16

| Requirement / NFR | Validation method | Acceptance criteria | Status |
|---|---|---|---|
| **REQ‑001 – Analog demodulation** | Functional test using known FM/AM/CW/USB/LSB signals; automated scripts verify correct demodulation and audio output.  Manual verification of audio quality and controls. | All five modes demodulate sample signals with SNR ≥30 dB; user can adjust frequency and bandwidth; no crashes. | Backlog |
| **REQ‑002 – Plugin architecture** | Unit tests for plugin API functions; integration tests loading/dropping plugins; attempt to load broken plugin and verify isolation. | Plugin loads/unloads without affecting other components; plugin can process data and produce output; invalid plugins are rejected gracefully. | Backlog |
| **REQ‑003 – Performance optimisation** | Automated performance tests measure audio latency and CPU utilisation on reference hardware; results logged. | Latency ≤150 ms and CPU utilisation ≤50 % for analog demodulation; see KPI‑01/02. | Backlog |
| **REQ‑004 – Multi‑receiver UI** | Manual tests: create multiple receivers with different settings; automated GUI tests using `pytest‑qt` to verify UI responsiveness. | User can add/remove receivers; UI remains responsive; no cross‑talk between receivers; thread stats visible. | Backlog |
| **REQ‑005 – Cryptanalysis module** | Unit tests for API calls; integration test using synthetic frequency‑hopping signal; evaluation of legal/ethical constraints. | Analysis module loads and produces correct hopping pattern; no leakage of sensitive data; user can enable/disable module. | Backlog |
| **NFR – Stability** | Long‑running tests (24 h) run with multiple receivers; monitor for crashes, memory leaks and unhandled exceptions. | Zero unhandled exceptions; memory usage remains bounded; CPU utilisation stable. | Backlog |
| **NFR – Configuration** | Attempt to run the application with various configuration combinations (defaults, env vars, CLI overrides); test validation logic. | Invalid configurations cause clear errors; overrides work according to the configuration strategy. | Backlog |
| **NFR – Logging** | Review log output under normal and error conditions; inspect rotation, format and content. | Logs contain timestamps, levels and context; errors are logged with stack traces; log files rotate at configured size. | Backlog |

**Status values:** `Backlog`, `Planned`, `In Progress`, `Validated`, `Failed`.

The validation matrix will grow as additional requirements and non‑functional requirements are defined.  Each row must be updated when the corresponding feature or requirement changes.