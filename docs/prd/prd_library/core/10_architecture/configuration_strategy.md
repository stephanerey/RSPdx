# Configuration Strategy

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.


**Last updated:** 2026-03-07

## Goal
Define where configuration lives, how it is loaded, how precedence works, and what is considered secret.

## Config sources
- Built-in defaults:
- Project file(s):
- Environment variables:
- CLI flags:
- Runtime UI overrides:

## Precedence
List from lowest to highest priority.
1. <...>
2. <...>
3. <...>

## Configuration categories
- Functional settings:
- Environment / deployment settings:
- Credentials / secrets:
- Developer-only flags:
- Experimental flags:

## File locations and formats
- Path:
- Format:
- Example:

## Validation rules
- Required keys:
- Type validation:
- Range validation:
- Fallback behavior:

## Secret handling
- Where secrets are allowed:
- Where secrets are forbidden:
- Redaction rules for logs:

## Acceptance criteria
- A newcomer can determine exactly how configuration is resolved.
- The application behavior is reproducible from declared configuration sources.
