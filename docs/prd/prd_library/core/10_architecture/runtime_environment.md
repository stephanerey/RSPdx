# Runtime environment

> **PRD Policy:** **PROJECT (editable)** — Define the supported platforms and run‑time conditions for the application.  This section clarifies dependencies and constraints for deployment.

**Last updated:** 2026‑03‑16

## Supported platforms

| Platform | Versions | Notes |
|---|---|---|
| **Windows** | Windows 10 (21H2+) and Windows 11 | Requires 64‑bit OS; installation of SDRplay API and SoapySDR drivers.  Use MSVC build tools to compile native extensions. |
| **Linux** | Ubuntu 20.04 LTS or newer; Debian 11; other recent x86‑64 distributions | Requires installation of SDRplay API (via `.deb` or `.tar.gz`) and SoapySDR packages.  GCC/Clang toolchain required for compiling C/C++ extensions. |
| **Other** | Not currently supported | macOS and ARM platforms (Raspberry Pi) may be explored in the future but are out of scope for MVP. |

## Toolchain & languages

- **Python:** Version **3.10** or later is required.  Virtual environments (`venv`, Conda) are recommended.  PyInstaller may be used for packaging.
- **C/C++:** A C compiler (GCC 9+, Clang 12+, or MSVC 2019+) is needed to build native extensions and plugin modules.  CMake will be used as the build system for C/C++ components.
- **SoapySDR & SDRplay API:** Must be installed and discoverable via the system library path.  The correct version matching the RSPdx firmware is required.
- **FFTW / DSP libs:** A fast Fourier transform library (e.g. FFTW) and any other DSP libraries must be available on the system or bundled with the application.  Appropriate headers must be installed for compilation.
- **Python packages:** `numpy`, `scipy`, `pyqt5`, `pyqtgraph`, `sounddevice` (PortAudio), `cffi`/`pybind11` for C bindings, `psutil` for metrics, `pytest`/`pytest-qt` for testing.

## Configuration & secrets

See `configuration_strategy.md` for a full description of configuration options and priority.  Runtime secrets (e.g. driver license keys) are not expected.  If any API keys or credentials become necessary, they must be injected via environment variables or secret management and never committed to the repository.

## Acceptance criteria

- The application can be installed and run on the supported platforms using documented installation steps.
- All native extensions compile successfully on Windows and Linux.  Automated builds verify cross‑platform compatibility.
- The application fails gracefully on unsupported platforms with a clear error message.