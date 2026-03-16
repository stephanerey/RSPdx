# Library Structure

## Objective
This library is a master repository used to instantiate project-specific PRDs.

## Sections
### `core/`
Universal project PRD skeleton.
Use it for every project regardless of implementation domain.

### `packs/`
Reusable specialized overlays.
Each pack adds domain-specific guidance, checklists, and expectations.
Packs are intentionally separate from the core to avoid polluting unrelated projects.

### `tools/`
Operational guidance for maintaining the library and later integrating automation.
This is where Codex-oriented skills and assembly helpers should live.

### `examples/`
Reserved for future example projects, sample compositions, or reference instantiations.

## Library governance rules
- The core must remain as neutral as possible.
- A pack must never duplicate the whole PRD backbone.
- Tools may describe processes, manifests, generators, or skills, but should not redefine project truth.
- Every change to a pack should preserve compatibility with the core model.
