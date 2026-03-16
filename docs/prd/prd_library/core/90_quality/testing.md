# Testing Strategy

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.


**Last updated:** 2026-03-07

## Goal
Define how the project is verified at each test layer and how contributors run those checks.

## Test layers
- Unit tests: fast and deterministic
- Integration tests: critical boundaries
- Smoke tests: minimal end-to-end checks
- Manual verification: operator-visible workflows when automation is not enough

## Coverage expectations
- New logic SHOULD have unit tests.
- Critical flows MUST have integration or smoke verification.
- Every shipped feature SHOULD map to at least one row in `validation_matrix.md`.

## Determinism and fixtures
- Test data / fixtures:
- Mock strategy:
- Randomness control:
- Time control:

## How to run
- Setup:
- Unit:
- Integration:
- Smoke:
- Manual:

## CI expectations
- Required checks:
- Optional checks:
- Artifact retention:
