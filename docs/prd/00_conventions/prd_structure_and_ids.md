# PRD Structure and IDs

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Last updated:** 2026-03-07

## Folder purpose
- `00_*` governance and stable conventions
- `01_*` product truth
- `02_*` tasks and phase tracking
- `03_*` traceability matrix
- `05_*` coding-agent prompts and handoff assets
- `10+` architecture / refactor / features / quality
- `95_*` source inputs

## Recommended IDs
### Requirement IDs
- Format: `REQ-###`
- Scope: product or system requirements worth tracing end-to-end

### Feature IDs
- Format: `F###`
- One feature spec per file
- Recommended filename: `F###_<short_name>.md`

### API IDs
- Format: `API###`
- One HTTP/RPC/service surface per file
- Recommended filename: `API###_<service_or_area>.md`

### Interface contract IDs
- Format: `IFC###`
- For non-HTTP interfaces: CLI, plugin contracts, signals, file formats, IPC, callbacks
- Recommended filename: `IFC###_<area>.md`

### Task IDs
- Format: `T-####`
- Prefix MAY encode phase, e.g. `T-30xx` for phase P30

### Decision IDs
- Product decision: `D-###`
- Architecture decision: `ADR-###`

### Validation IDs
- Format: `VAL-###`
- Used in `90_quality/validation_matrix.md`

## Cross-references
- Every feature spec MUST link to impacted architecture docs and quality constraints.
- Every interface spec MUST define examples, failure modes, and verification notes.
- Every PR or merge request SHOULD reference the relevant PRD files and verification steps.
- The traceability matrix SHOULD connect `REQ` → `F/API/IFC` → `T` → `VAL`.

## Versioning
- Use `Last updated` at the top of living docs.
- Snapshots are immutable.
- ADR files are append-only after acceptance, except for explicit supersession notes.
