# Feature Spec Guidelines

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


## Mandatory sections
- Goal
- Non-goals
- Scenarios
- Interfaces
- Edge cases
- Constraints
- Acceptance criteria
- Testing notes
- Traceability refs

## IDs and naming
- Feature ID: `F###`
- Filename: `F###_<short_name>.md`

## Traceability
Feature specs MUST link to:
- impacted architecture docs (`10_architecture/*`)
- relevant quality requirements (`90_quality/*`)
- requirement IDs when the project uses them
- validation rows when known

## When to use which template
- Use `feature_template.md` for behavior and user-visible/system-visible capability.
- Use `api_spec_template.md` for HTTP/RPC/service contracts.
- Use `interface_contract_template.md` for CLI, plugin, signals, file formats, IPC, callbacks, and other non-HTTP interfaces.
