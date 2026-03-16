# Logging and error strategy

> **PRD Policy:** **PROJECT (editable)** — Define how the application logs information and handles errors.  Consistent logging aids debugging and observability.

**Last updated:** 2026‑03‑16

## Logging

- **Format:** All log entries follow a structured format: `[timestamp] [level] [component] message (context)`.  Timestamps use ISO 8601 in UTC.  Context includes thread ID, receiver ID and plugin name where applicable.
- **Levels:** Use standard log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
  - `DEBUG`: Detailed information for developers (e.g. intermediate DSP values), disabled by default.
  - `INFO`: High‑level events like starting/stopping devices, loading plugins, user actions.
  - `WARNING`: Recoverable problems such as dropped samples or minor configuration issues.
  - `ERROR`: Serious problems requiring user attention; the application attempts to recover or shuts down gracefully.
  - `CRITICAL`: Unrecoverable errors leading to immediate termination; rare.
- **Destinations:** Logs are written to both the console and a rotating log file (`logs/rspdx.log`).  A logging configuration file (`logging.yaml`) defines handlers, formatters and rotation policies (e.g. max 10 MB per file, 5 backups).
- **Thread safety:** Use thread‑safe loggers and avoid logging inside tight loops (move to debug level or batch messages) to minimise overhead.
- **Integration:** Plugins may obtain a logger instance via the plugin API; plugin logs are prefixed with the plugin name.

## Error handling

- **Exceptions:** All unexpected exceptions must be caught at the appropriate layer and either handled or escalated with context.  Never silently ignore exceptions.
- **Classification:** Define custom exception classes (e.g. `HardwareError`, `PluginError`, `ConfigurationError`, `DSPError`) to classify errors and facilitate targeted handling.
- **User feedback:** When an error affects the user (e.g. device not found, plugin load failure), display a descriptive message in the UI and log details at `ERROR` level.  Provide guidance on remediation if possible.
- **Fail‑fast vs graceful degradation:** Critical errors (e.g. invalid configuration, corrupted plugin) should prevent the application from starting or loading that component.  Non‑critical errors (e.g. plugin processing error) should deactivate the affected plugin while allowing others to continue.
- **Crash reporting:** In development builds, enable optional crash dumps and stack traces; in release builds, suppress them unless explicitly enabled by the user.  Encourage users to submit error reports via GitHub issues.

## Observability

- **Metrics:** Use `psutil` and ThreadManager metrics to record CPU utilisation, memory usage and thread counts.  Expose these via the UI’s diagnostic panel.
- **Instrumentation hooks:** Provide hooks for plugins to record metrics (e.g. demodulator throughput, error vector magnitude) and forward them to the data storage or logging subsystem.

## Acceptance criteria

- Logging output is structured, configurable and minimal overhead.  It can be enabled/disabled via configuration.
- Errors are categorised and communicated clearly to the user and developer.  No unhandled exceptions reach the top level.
- Logs and metrics provide sufficient information to diagnose performance issues and plugin failures.