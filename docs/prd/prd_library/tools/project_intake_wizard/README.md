# Project Intake Wizard

This tool helps a human start a project PRD without having to understand the whole library first.

## Goal
Collect the minimum useful project framing, suggest relevant packs, and generate the first files that GPT can use to complete the PRD cleanly.

## Outputs
The wizard generates:
- `PROJECT_INTAKE.md`
- `PROJECT_PROFILE.md`
- `PACKS_ACTIVE.md`
- `NEXT_STEPS_FOR_GPT.md`

These files are intentionally short and operational.
They do **not** replace the PRD. They accelerate the first PRD pass.

## Two supported modes
### 1. Interactive questionnaire
Use this when the human wants to answer guided questions directly.

```bash
python run_wizard.py \
  --mode interactive \
  --output-dir /path/to/generated_intake
```

Direct internal call:
```bash
python prd_library/tools/project_intake_wizard/wizard.py \
  --mode interactive \
  --output-dir /path/to/generated_intake
```

### 2. Structured brief parsing
Use this when the human prefers to write a first brief in markdown.
The brief should follow the headings of `input_templates/PROJECT_BRIEF_TEMPLATE.md`.

```bash
python run_wizard.py \
  --mode brief \
  --input-file /path/to/your_filled_brief.md \
  --output-dir /path/to/generated_intake
```

Direct internal call:
```bash
python prd_library/tools/project_intake_wizard/wizard.py \
  --mode brief \
  --input-file /path/to/your_filled_brief.md \
  --output-dir /path/to/generated_intake
```

In practice you should copy the template first, fill it, then pass the filled file to the wizard.

## Recommended workflow
1. Instantiate a project PRD from `core/`.
2. Run the wizard and point `--output-dir` directly to the project PRD root.
3. Review the generated intake files and pack suggestions.
4. Import only the packs that really apply.
5. Ask GPT to read the generated intake files and fill the PRD.
6. If the project will use Codex, instantiate `AGENTS.md` and related templates from `prd_library/tools/codex/templates/`.
7. Only then ask Codex to implement targeted slices.

## Important limitation
Pack suggestions are heuristics.
They are useful defaults, not automatic truth.
A human or GPT should still validate them.

## Files provided here
- `wizard.py` — the actual wizard
- `input_templates/PROJECT_BRIEF_TEMPLATE.md` — structured brief to fill manually
- `input_templates/PROJECT_INTAKE_TEMPLATE.md` — manual compact intake template
- `examples/` — example brief and generated outputs
