# External dependencies

> **PRD Policy:** **PROJECT (editable)** — Identify third‑party libraries, tools and services used by the project.  Document their purpose, version constraints, licenses and criticality.

**Last updated:** 2026‑03‑16

| Dependency | Type | Purpose / description | Required version | License | Criticality | Notes |
|---|---|---|---|---|---|---|
| **SoapySDR** | Library | Hardware abstraction layer used to access SDR devices, including the SDRplay RSPdx.  Provides a uniform API for multiple SDRs. | 0.8 or later | LGPL | High | Must be compiled and installed on target systems.  Used by the device controller. |
| **SDRplay API** | Library | Vendor‑supplied API for the RSPdx; required by SoapySDR RSPplay module. | Latest RSPdx release (e.g. v3.x) | Proprietary (redistribution restrictions) | High | Download from SDRplay website.  Must match firmware version. |
| **FFTW / KissFFT / Intel IPP** | Library | Performs fast Fourier transforms for spectral analysis and filtering. | FFTW 3.3+ or KissFFT 1.3+ | GPL/LGPL/MIT | High | Only one FFT library will be selected based on licensing and performance. |
| **numpy** | Python package | Provides n‑dimensional arrays and vectorised operations for DSP and buffer management. | ≥1.24 | BSD | High | Required for almost all processing. |
| **scipy** | Python package | Supplies signal‑processing routines (filters, resamplers) for prototyping; heavy lifting offloaded to C libraries. | ≥1.10 | BSD | Medium | Used primarily during prototyping; may be replaced by custom C implementations for performance. |
| **PyQt5** | Python package | GUI framework for building the application’s user interface. | ≥5.15 | GPL/LGPL | High | Provides widgets, signals/slots and platform integration.  Alternative: PySide6. |
| **PyQtGraph** | Python package | Real‑time plotting library used for spectrum, waterfall and constellation displays. | ≥0.13 | MIT | High | Built on PyQt5; must handle large streaming datasets efficiently. |
| **sounddevice / PortAudio** | Python package / C library | Sends demodulated audio to the system’s audio device; wraps PortAudio with a Python API. | `sounddevice` ≥0.4, PortAudio ≥19 | MIT | High | May need alternative for Windows vs Linux; ensures low latency audio output. |
| **cffi / pybind11 / Cython** | Python package | Bindings to call C/C++ DSP routines from Python. | Latest stable | MIT/BSD | Medium | Choice depends on plugin implementation; must support cross‑platform compilation. |
| **psutil** | Python package | Gathers CPU, memory and thread statistics for performance monitoring. | ≥5.9 | BSD | Medium | Used by ThreadManager UI to display resource usage. |
| **pytest / pytest‑qt** | Python package | Testing framework and Qt integration for unit and integration tests. | ≥7.0 | MIT | Medium | Enables automated testing of core and UI components. |
| **PyInstaller** | Python package | Bundles the application into a standalone executable for distribution. | ≥6.0 | GPL | Low | Only used during packaging phase. |

Additional dependencies may be added as features evolve.  Each new dependency must be documented here with its purpose and license.