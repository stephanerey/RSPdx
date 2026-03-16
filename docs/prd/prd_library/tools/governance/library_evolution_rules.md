# Library Evolution Rules

## Goals
Keep the library stable enough for reuse while still allowing growth.

## Rules
- Changes to `core/` should remain generic.
- Domain-specific concerns should move into packs.
- New packs must follow `packs/PACK_STANDARD.md`.
- Tooling notes must not silently redefine the core model.
- Future Codex skills must align with the structure and naming rules of the PRD library.
