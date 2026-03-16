# Configuration strategy

> **PRD Policy:** **PROJECT (editable)** — Describe how runtime configuration values are provided, validated and overridden.  A clear strategy prevents hidden magic numbers and makes behaviour predictable.

**Last updated:** 2026‑03‑16

## Sources of configuration

Configuration parameters may originate from several sources.  They are applied in the following precedence order (highest to lowest):

1. **Command‑line arguments (CLI):** Any parameter explicitly passed on the command line overrides all other values.  For example, `--sample-rate=2048000` or `--freq=145.500e6`.
2. **UI overrides:** Settings adjusted via the GUI (frequency, bandwidth, demodulator selection) take effect immediately and persist for the session, but not across restarts unless saved to config.
3. **Environment variables:** Values exported in the environment, prefixed by `RSPDX_` (e.g. `RSPDX_SAMPLE_RATE=2048000`), override configuration file defaults.
4. **Configuration file (`config.yaml`):** A YAML file loaded at startup; contains persistent defaults for device selection, sample rate, gain profiles, UI preferences and plugin paths.  Stored in the user’s home directory or alongside the executable.
5. **Built‑in defaults:** If no values are provided, sensible defaults are applied (e.g. sample rate of 2 MHz, FM demodulation, default antenna).

## Validation & schema

- A configuration schema (e.g. using `pydantic` or `voluptuous`) defines all supported parameters, their types, allowed ranges and default values.
- At startup, the application loads the configuration file, environment variables and CLI arguments, validates them against the schema and applies precedence rules.  Invalid values cause a descriptive error and abort the start‑up.
- The schema is documented in `config_schema.md` (to be created) and enforced by automated tests.

## Secrets handling

The application is not expected to use secrets.  Should any sensitive information (API keys, tokens) be introduced in future, it must be supplied via environment variables or secret management services and excluded from configuration files.  Secrets must never be logged or exposed in the UI.

## Acceptance criteria

- All configurable parameters are documented with default values and descriptions.
- Overrides work as expected: CLI > UI > env vars > config file > defaults.
- Invalid or unknown configuration options cause an informative error.