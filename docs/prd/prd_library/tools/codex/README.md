# Codex Integration Area

This folder contains Codex-oriented assets and operating guidance for the PRD library.

## Contents
- `CODEX_OPERATING_MODEL.md` — how to split work between GPT and Codex
- `INSTRUCTION_DISCOVERY_NOTES.md` — how Codex discovers AGENTS files and related limits
- `templates/` — starter assets for `AGENTS.md`, `AGENTS.override.md`, and `PLANS.md`
- `prompts/` — reusable prompt patterns for domain-first and implementation passes
- `skills/` — skill templates, policy, and evaluation checklist

## Design rule
Keep the repository truth in versioned docs. Use Codex assets to help enforce that truth, not to replace it.

## Recommended minimum repo bootstrap
For projects that will use Codex regularly, start with:
- a short repo-level `AGENTS.md`
- optional local `AGENTS.override.md` near specialized subtrees
- optional `PLANS.md` for long or multi-step work
- repo-local skills under `.agents/skills/` only when the workflow is truly reusable
