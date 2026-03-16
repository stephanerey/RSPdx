# External Dependencies

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.


**Last updated:** 2026-03-07

## Goal
Track critical third-party components, system dependencies, and external services.

## Dependency inventory
| Name | Type | Purpose | Required version | License | Criticality | Notes |
|---|---|---|---|---|---|---|
| <dependency> | <lib/tool/service> | <...> | <...> | <...> | <low/med/high> |  |

## Rules
- Record anything that can block build, runtime, deployment, or validation.
- Call out dependencies with restrictive licenses or fragile version constraints.
- Link high-risk dependency decisions to ADRs when needed.

## Acceptance criteria
- The project can be bootstrapped without hidden third-party assumptions.
