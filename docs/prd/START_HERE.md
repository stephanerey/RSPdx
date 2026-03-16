# START HERE

This repository is intentionally split into two layers:
- human-facing entry documents at the root
- the actual reusable library under `prd_library/`

## Recommended reading order
1. `README.md`
2. `README_FR.md` or `README_EN.md`
3. `QUICKSTART.md`
4. `run_wizard.py` or `prd_library/tools/project_intake_wizard/README.md`
5. `prd_library/README.md`
6. `prd_library/LIBRARY_STRUCTURE.md`
7. `prd_library/PROJECT_ASSEMBLY_MODEL.md`

## If you want the shortest path
- start with `QUICKSTART.md`
- copy `prd_library/core/` into a new project PRD folder
- run the intake wizard and point `--output-dir` to that project PRD root
- review the generated intake files
- select the relevant packs from `prd_library/packs/`
