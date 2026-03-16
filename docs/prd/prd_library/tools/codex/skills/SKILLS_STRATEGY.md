# Skills Strategy

## Role of skills in this library
Skills are not the PRD.
Skills are reusable workflows that help Codex apply the PRD more reliably.

## Recommended layering
- `AGENTS.md` = persistent repo rules and routing guidance
- PRD = project truth
- domain docs = business truth when needed
- skills = reusable workflows
- MCP = live external context when the truth lives outside the repo

## Good candidates for skills
- project state summarizer
- PRD gap reviewer
- requirements to tasks converter
- feature contract reviewer
- quality gate reviewer
- as-built drift reviewer

## Bad candidates for skills
- full project PRD duplication
- unstable product specs
- giant architecture dumps
- project truth that should live in versioned docs

## Storage convention
Use official Codex skill locations where possible:
- personal skills: `$HOME/.agents/skills`
- repo skills: `.agents/skills`

If a local setup uses an additional custom path, document it explicitly in the repo, but do not make the library depend on a non-standard location by default.


## Evaluation habit
Do not treat a skill as finished when it is first written.
Review whether it triggers reliably, whether it loads the right amount of context, and whether it actually improves repeatability.
Use `SKILL_EVAL_CHECKLIST.md` when a skill starts to matter operationally.
