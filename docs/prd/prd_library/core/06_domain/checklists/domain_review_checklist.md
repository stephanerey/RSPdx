# Domain Review Checklist

Use this checklist before accepting a domain-heavy implementation.

## Domain understanding
- Are the core domain objects correctly identified?
- Are the mandatory relations explicit in the code and UI?
- Are domain states represented clearly?

## UI meaning
- Does the UI preserve domain meaning instead of collapsing everything into generic CRUD?
- Is critical information visible without unnecessary indirection?
- Are actions shown in the right business context?

## AI / automation
- Are AI outputs clearly marked as suggestion / evidence / inference / action when needed?
- Is human validation required where the domain expects it?
- Is uncertainty shown honestly?

## Traceability
- Can we trace an action back to the relevant requirement, module, or rule?
- Does the implementation contradict the domain kernel or doctrine?

## Common failure modes
- Missing parent context
- orphan entities
- fake certainty
- hidden critical information
- state transitions not enforced
- technically valid but business-invalid UI
