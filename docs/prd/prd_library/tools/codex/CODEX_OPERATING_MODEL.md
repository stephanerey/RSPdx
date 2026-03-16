# Codex Operating Model

## Principle
Use GPT for broad reasoning, research, spec design, and PRD shaping.
Use Codex for repository-local reading, adaptation to the actual codebase, implementation, validation, and iterative maintenance.

## Practical split
### GPT is best for
- project framing
- deep reasoning
- architecture exploration
- PRD authoring
- domain modeling
- large synthesis work

### Codex is best for
- reading the repository
- following repo instructions
- editing files
- running commands and tests
- updating implementation-aligned docs
- executing narrow slices of work

## Most important rule
Do not throw a huge unstructured PRD at Codex and expect it to infer the domain perfectly.
Give Codex a short hierarchy of truth.

## Recommended hierarchy for Codex
1. local `AGENTS.md`
2. domain kernel and transverse doctrine when relevant
3. module doc
4. critical screen doc if relevant
5. targeted feature / architecture documents
6. only then the implementation task

## Two-pass working method
### Pass A — domain / design understanding
Ask Codex to:
- read only the few relevant files
- restate the business model or implementation intent
- list invariants
- identify ambiguities
- propose a short implementation plan
- not code yet

### Pass B — implementation
Once the summary is validated, ask Codex to:
- implement only the targeted slice
- respect the listed invariants
- state files changed
- state DB / API / UI impacts
- update the related docs if needed

## What to keep small
- `AGENTS.md`
- domain kernel
- module docs
- screen docs
- prompts given to Codex

## What to avoid
- giant prose documents for every screen
- repeating the full PRD inside a skill
- hiding project truth in a chat history only
- relying only on global instructions when the repo needs local rules
