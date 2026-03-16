# Domain Layer

Use this section when the project depends on a strong business, operational, or applicative logic that a coding agent is unlikely to infer reliably from technical specs alone.

Typical cases:
- industry-specific workflows
- recruitment / HR
- accounting / finance operations
- laboratory or accelerator operations
- support tooling with role-dependent flows
- regulated or approval-heavy workflows

## Goal
Turn diffuse business knowledge into short, explicit, actionable documents that Codex can follow before coding.

## Recommended order
1. `01_DOMAIN_KERNEL.md`
2. `02_TRANSVERSE_DOCTRINE.md`
3. `modules/*`
4. `screens/*` only for critical screens
5. `checklists/domain_review_checklist.md`

## Sizing rule
Keep these docs compact:
- domain kernel: about 2 to 4 pages
- module doc: about 1 to 2 pages
- critical screen doc: about 1 page

The goal is not to write novels.
The goal is to make the domain executable by an agent.
