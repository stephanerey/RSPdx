# Pack Standard

## Purpose
Define the standard structure and governance rules for every pack in the PRD library.

## Pack design goals
A pack must:
- solve a recurring specialization need
- stay smaller than the core
- add guidance without duplicating project truth
- map its impact back into the core PRD

## Required files in every pack
1. `README.md`
   - pack purpose
   - intended project families
   - when to use it
   - when not to use it

2. `pack_manifest.md`
   - pack identifier
   - version
   - owner
   - compatibility notes
   - required core impacts

3. `activation_checklist.md`
   - criteria to decide whether the pack applies
   - minimum prerequisites before activating it

4. `required_core_impacts.md`
   - which core documents must be filled or strengthened when the pack is active
   - mandatory additions to requirements, architecture, tasks, and quality

5. `architecture_overlay.md`
   - architecture concerns specific to the pack domain

6. `quality_overlay.md`
   - test, validation, and non-functional expectations specific to the pack domain

7. `tasks_overlay.md`
   - recurring implementation or integration tasks typically needed by projects using this pack

## Optional files
- `requirements_overlay.md`
- `deployment_overlay.md`
- `examples.md`
- `domain_glossary.md`
- `integration_notes.md`
- `skills/` for pack-specific Codex skill guidance later

## Rules
- Keep file names stable across packs whenever possible.
- Use the same semantics across packs.
- Refer back to core docs instead of redefining them.
- If a pack requires a new standard file, update `_pack_template/` and this standard.
