# Domain Kernel

> Fill this document when the project has a real métier / operational logic that must be understood explicitly by a coding agent.

## Finality
Describe the minimal domain truth that must be understood before modifying the product.

## Core domain objects
- Object A:
- Object B:
- Object C:

For each object, state:
- what it is
- who uses it
- why it matters
- what it is related to

## Mandatory relations
- A -> B : required / optional
- B -> C : required / optional
- A -> C : required / optional

## Domain invariants
List the things that must remain true everywhere.
Examples:
- An entity cannot exist without its parent context.
- A recommendation without evidence is not displayed as a fact.
- A workflow state cannot skip validation.

## Minimal domain states
### Object A
- draft
- active
- blocked
- archived

### Object B
- pending
- validated
- rejected

## Roles and visibility
- Role 1 can:
- Role 2 can:
- Role 3 can:

## Human-in-the-loop rules
- What AI may propose
- What AI must never do automatically
- What always requires human validation

## UI rules derived from the domain
- What must always be visible
- What may be secondary
- What must never be hidden only behind hover

## Anti-patterns
List the recurring wrong implementations a coding agent should avoid.
