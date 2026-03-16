# Skill Evaluation Checklist

Use this when a skill becomes important enough to maintain deliberately.

## Trigger quality
- [ ] The `name` is unambiguous.
- [ ] The `description` clearly states when the skill should trigger.
- [ ] The `description` clearly states when the skill should not trigger.

## Scope control
- [ ] The skill solves one repeatable job only.
- [ ] The skill does not duplicate the full project PRD.
- [ ] The skill does not hide project decisions that should live in docs.

## Context efficiency
- [ ] The instructions are short enough to load efficiently.
- [ ] Optional references and scripts are included only when they materially help.
- [ ] The skill does not force excessive context for small tasks.

## Operational value
- [ ] The skill reduces repeated prompting.
- [ ] The skill improves result consistency.
- [ ] The skill is easier to maintain than repeating the workflow manually.

## Validation
- [ ] The skill has been tried on at least a few representative tasks.
- [ ] Known failure modes or non-goals are documented.
- [ ] The team knows where the skill should be installed (`.agents/skills` or `$HOME/.agents/skills`).
