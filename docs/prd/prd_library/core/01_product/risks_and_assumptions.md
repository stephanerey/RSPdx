# Risks and assumptions

> **PRD Policy:** **PROJECT (editable)** — Identify risks and capture assumptions that underpin the project.  Keep this list up to date as you learn more.

**Last updated:** 2026‑03‑16

## Risks

| ID | Description | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **R‑001 – Hardware API instability** | Changes to the SDRplay API or driver on Windows/Linux could break the SoapySDR integration. | Medium | High: application may not run or produce correct IQ samples. | Monitor vendor release notes; encapsulate hardware access behind an abstraction layer; maintain automated integration tests. |
| **R‑002 – Performance shortfall** | Pure Python code may not meet latency and CPU targets; C/C++ integration could be challenging. | High | High: poor user experience, dropped samples. | Use proven DSP libraries (FFTW, Intel IPP), profile early, and allocate time for optimisation in P60.  Consider multi‑threading and vectorised operations. |
| **R‑003 – Plugin API complexity** | Designing a stable plugin interface that is easy to use yet flexible may be harder than anticipated. | Medium | Medium: delays in delivering digital modes and third‑party plugins. | Study SDR++ and other plugin frameworks, prototype early, and solicit feedback from potential plugin developers. |
| **R‑004 – Cryptanalysis legal/ethical issues** | Implementing cryptanalysis modules may implicate legal regulations or ethical concerns depending on the signals analysed. | Low | Medium: project may need to exclude certain features or restrict distribution. | Research applicable laws, restrict cryptanalysis to signals the user is legally allowed to monitor, and provide clear warnings in documentation. |
| **R‑005 – Resource constraints** | Limited developer time could lead to slipping deadlines or reduced scope. | Medium | Medium: roadmap delays and incomplete features. | Prioritise MVP and core architecture.  Defer less critical features to later phases.  Seek contributions from the open‑source community. |

## Assumptions

| AID | Assumption | Justification | Consequence if false |
|---|---|---|---|
| **A‑001 – Availability of SoapySDR and SDRplay drivers** | We assume SoapySDR and the SDRplay API will continue to be available and functional on supported platforms. | Both libraries are maintained and widely used; current RSPdx prototype runs on them. | If the libraries are deprecated or broken, we must find or develop alternative drivers, delaying the project. |
| **A‑002 – Python 3.10+ remains stable** | We assume that Python 3.10 and later will remain supported and available on target platforms during development. | Python 3.10 is a long‑term support release with widespread adoption. | If Python 3.10 is deprecated or incompatible with dependencies, we must upgrade or pin to a different version, affecting compatibility. |
| **A‑003 – Community interest in plugins** | We assume there will be interest from radio amateurs and researchers to develop third‑party plugins once the framework is released. | Similar projects like SDR++ show active plugin ecosystems. | If few third‑party plugins appear, we may need to develop more digital modes in‑house to meet user expectations. |
| **A‑004 – RSPdx hardware remains available** | We assume that the SDRplay RSPdx device will continue to be sold and supported by the vendor. | The RSPdx is a recent device with a strong user base. | If the hardware becomes unavailable, the project may need to support alternative devices sooner than planned. |
