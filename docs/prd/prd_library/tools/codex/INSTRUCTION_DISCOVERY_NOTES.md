# Instruction Discovery Notes

## Goal
Summarize the practical instruction-discovery behavior that matters when integrating Codex with this PRD library.

## Global scope
Codex first checks its home directory for global instructions:
- `AGENTS.override.md`
- otherwise `AGENTS.md`

Default Codex home is `~/.codex`, unless `CODEX_HOME` is set.

## Project scope
From the repository root down to the current working directory, Codex checks each directory in this order:
1. `AGENTS.override.md`
2. `AGENTS.md`
3. any fallback filenames configured in `project_doc_fallback_filenames`

Codex includes at most one instruction file per directory. Files closer to the current working directory win because they are appended later in the combined prompt.

## Size limit
Combined instruction size is capped by `project_doc_max_bytes` in Codex configuration.
If instructions grow too large, keep root `AGENTS.md` short and move specialized guidance into nearby overrides or referenced docs.

## Practical implication for this library
- keep the repo root `AGENTS.md` short and operational
- put durable repo rules in `AGENTS.md`
- put subtree-specific rules in `AGENTS.override.md` near the relevant code
- keep project truth in the PRD and domain docs, then route Codex to those docs from `AGENTS.md`
- use fallback filenames only if the repository already has a strong convention that should not be broken
