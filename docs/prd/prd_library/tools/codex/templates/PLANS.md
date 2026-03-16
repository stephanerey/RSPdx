# PLANS.md

## Purpose
Use this file for long, ambiguous, or multi-step work that needs a reviewable execution plan before code changes land.

## When to use
- significant refactor
- cross-cutting feature
- migration
- work with many unknowns
- change that spans several modules or services

## ExecPlan template

### Title
Short name of the plan.

### Goal
What should be true when the work is complete.

### Context
Relevant repository paths, PRD docs, domain docs, constraints, and known pain points.

### Non-negotiable invariants
List the behaviors, contracts, and constraints that must remain true.

### Assumptions and unknowns
Record what is assumed and what still needs validation.

### Milestones
1. Milestone name
   - expected outcome
   - files or areas likely impacted
   - validation method
2. ...

### Verification
Commands, tests, manual checks, and acceptance signals.

### Decision log
Keep a dated log of important decisions or scope adjustments.

### Progress log
Record what has been completed and what remains.
