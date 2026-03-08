# Logging and Errors

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.


**Last updated:** 2026-03-07

## Goal
Standardize logging, diagnostics, error handling, and operator-facing behavior.

## Logging policy
### Format
- Timestamp:
- Level:
- Logger / component:
- Correlation key:
- Message style:

### Levels
- `DEBUG`: <...>
- `INFO`: <...>
- `WARNING`: <...>
- `ERROR`: <...>
- `CRITICAL`: <...>

### Destinations
- Console:
- File:
- UI / operator surface:
- Telemetry / metrics:

### Rotation and retention
- Rotation policy:
- Retention:
- Size limits:

## Error policy
### Error classes
- User error:
- Recoverable runtime error:
- Non-recoverable runtime error:
- Dependency / environment error:
- Data / contract violation:

### Propagation rules
- Background-task errors:
- UI-visible errors:
- API / interface errors:
- Retry / backoff:
- Fallback behavior:

## Diagnostics and observability
- Health indicators:
- Performance counters:
- Debug toggles:
- Crash / incident artifacts:

## Acceptance criteria
- Failures are visible and actionable.
- Logs are sufficient to reproduce or triage critical issues.
- User-facing errors are understandable and not silent.
