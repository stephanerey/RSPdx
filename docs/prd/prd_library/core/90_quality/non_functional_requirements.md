# Non‑Functional Requirements (NFR)

> **PRD Policy:** **PROJECT (editable)** — Define the non‑functional requirements that the system must meet.  These set performance budgets, reliability goals, security expectations and maintainability targets.

**Last updated:** 2026‑03‑16

## Performance and resource budgets

- **Startup time:** The application should launch and initialise the SDR device within **5 seconds** on reference hardware.
- **Steady‑state latency:** End‑to‑end latency from sample acquisition to audio output must be ≤150 ms for analog demodulation (see KPI‑01).
- **Throughput:** The system should handle a continuous IQ stream at **2 megabytes per second** (2 Msps complex) without dropping samples.
- **CPU budget:** Average CPU utilisation while demodulating one analog receiver and rendering the spectrum must not exceed **50 %** on a quad‑core Intel i5 (see KPI‑02).  Additional receivers may add up to 20 % each.
- **Memory / RAM budget:** Total memory usage should remain under **500 MB** during normal operation; ring buffers and FFT buffers must release memory when receivers are closed.
- **Storage / disk budget:** Log files and cache directories must not exceed **100 MB** by default; implement log rotation and automatic cleanup.
- **Network / bus budget:** No network communications are expected in MVP.  Future remote control features must limit outbound connections and support proxy configuration.
- **Power / thermal budget:** Not explicitly targeted; avoid excessive CPU usage to prevent overheating on laptops.

## Reliability and recovery

- **Expected uptime / session stability:** The application should run continuously for **24 hours** without crashing or leaking memory.
- **Timeout policy:** Attempt to connect to the SDR device with a timeout of **5 seconds**; plugin operations may specify their own timeouts.  UI actions must respond within **200 ms**.
- **Retry policy:** On hardware disconnection, the device controller retries connection every **10 seconds** up to 3 times before prompting the user.
- **Recovery behaviour after failure:** If a plugin throws an exception, the plugin manager unloads it and the application continues running.  If the device fails, the user is offered a chance to reconnect or exit.
- **Data‑loss tolerance:** Audio and spectrum data are transient; loss of data during a brief glitch is acceptable.  However, if recording is enabled, file integrity must be ensured with proper closing on exit.
- **Safe‑state / fallback behaviour:** On unrecoverable errors, shut down the device and threads, save logs and exit gracefully.  Avoid leaving the SDR in an inconsistent state.

## Security and privacy

- **Secret handling:** No credentials or API keys are currently required.  Should secrets be introduced, they must be passed via environment variables and never stored in plain text.
- **Sensitive data rules:** Cryptanalysis modules may decode protected communications.  The software must not store or transmit such data without explicit user action.  Users are responsible for legal compliance when decoding signals.
- **Authentication / authorisation expectations:** The application runs locally and does not expose network services in MVP.  Future remote control features must implement authentication (e.g. token‑based) before accepting connections.
- **Auditability needs:** All plugin loads, errors and critical operations should be logged with timestamps to support forensic analysis if needed.

## Observability and diagnostics

- **Required logs:** Structured logs must capture device events (connect/disconnect), plugin lifecycle events (load/unload), errors, warnings, and performance metrics.  See `logging_and_errors.md` for format.
- **Required metrics:** Expose CPU and memory usage, thread counts, and per‑receiver latency metrics via the diagnostics panel.  Provide hooks for plugins to report their own metrics.
- **Required traces / correlation IDs:** When processing IQ data, attach correlation IDs to track data through threads and plugins if needed for debugging race conditions.
- **Crash diagnostics:** In development builds, enable crash dumps (core dumps on Linux, minidumps on Windows) and stack traces.  Release builds may disable core dumps by default.
- **Bench / field debug hooks:** Provide an optional debug mode that increases log verbosity, enables GUI overlays (e.g. filter taps, constellation points) and records intermediate signals to disk.

## Compatibility and portability

- **Supported OS / runtimes / toolchains:** See `runtime_environment.md` for detailed platform support.
- **Supported dependency versions:** External dependencies must conform to the versions listed in `external_dependencies.md`.  Upgrading a dependency requires verifying compatibility.
- **Backward compatibility constraints:** Changes to the plugin API must maintain compatibility within a major version.  Configuration files must remain valid across minor versions; provide migration scripts if formats change.
- **Upgrade / migration constraints:** The installer/upgrader must not overwrite user configuration without confirmation.  Provide documentation on how to migrate plugins to new versions.

## Maintainability

- **Code health constraints:** Adhere to PEP 8 and project coding standards.  Use type hints and static analysis (e.g. `mypy`) to catch errors early.
- **Modularity expectations:** Keep modules small and focused; avoid circular dependencies.  Plugin API must be clearly separated from core logic.
- **Documentation expectations:** All public classes, functions and plugin interfaces must have docstrings.  Major design decisions are documented in `decisions.md` and architecture files.  The user manual should describe installation, operation and plugin development.
- **Maximum tolerated complexity hotspots:** Complex DSP code may accumulate in native modules; accompany such code with diagrams and comments explaining algorithms.  Regular code reviews help maintain readability.