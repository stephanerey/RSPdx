# PRD Structure and IDs

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


## Folder purpose
- `00_*` governance and stable conventions
- `01_*` product (living source of truth)
- `02_*` tasks (phases + snapshots)
- `05_*` coding agent prompts / handoff / execution plans
- `10+` application specs (architecture, refactor, features, quality)
- `95_*` sources (inputs)

## IDs
### Feature IDs
- Format: `F###` (3 digits)
- One feature spec per file or per feature folder. Recommended filename: `F###_<short_name>.md`

### API IDs
- Format: `API###`
- One endpoint group or service per file. Recommended: `API###_<service_or_area>.md`

### Task IDs
- Format: `T-####` (4 digits recommended)
- Prefix may encode phase: e.g. `T-30xx` for phase P30.

## Cross-references
- Every feature spec MUST link to impacted architecture docs and quality constraints.
- Every API spec MUST include request/response examples and error codes.
- Every PR/merge request MUST reference the relevant PRD files and list verification steps.

## Versioning
- Use “Last updated” at top of living docs.
- Snapshots are immutable.
