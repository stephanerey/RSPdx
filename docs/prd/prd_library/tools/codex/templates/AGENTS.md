# AGENTS.md

## Repository expectations
- Read `PRD/START_HERE.md` or the local PRD entry point before editing project-critical code.
- For domain-heavy work, read the domain kernel and the relevant module doc before implementation.
- Keep changes scoped to the requested slice.
- Prefer updating existing files and patterns rather than introducing parallel structures.

## How to work in this repository
- Build command: `<fill>`
- Test command: `<fill>`
- Lint / static analysis command: `<fill>`
- Packaging / deployment check: `<fill or n/a>`

## Constraints and do-not rules
- Do not add production dependencies without checking project conventions.
- Do not invent undocumented domain behavior when a PRD or domain doc exists.
- Do not hide architecture decisions only in code comments or chat.
- Update tests and docs when behavior or project truth changes.

## Done when
- requested behavior is implemented
- relevant tests or validation commands pass
- impacted docs are updated when needed
- changed files and impacts are summarized clearly

## Planning rule
For complex features, major refactors, ambiguous changes, or work expected to span many steps, use Plan mode or follow `PLANS.md` before implementation.
