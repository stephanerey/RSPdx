#!/usr/bin/env python3
"""Project intake wizard for prd_library.

This tool helps a human collect the minimum information required to start a
project PRD. It supports two entry modes:
1. interactive questionnaire
2. parsing of a structured markdown brief template

Outputs:
- PROJECT_INTAKE.md
- PROJECT_PROFILE.md
- PACKS_ACTIVE.md
- NEXT_STEPS_FOR_GPT.md
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Dict, List, Optional

PROJECT_TYPES = [
    "web_app",
    "backend_service",
    "desktop_app",
    "python_tool",
    "cli",
    "library",
    "c_embedded",
    "mixed",
]

LIFECYCLES = ["greenfield", "refactor", "maintenance", "migration", "research"]
CRITICALITIES = ["low", "medium", "high", "safety-sensitive"]
DELIVERY_MODES = ["prototype", "internal tool", "production", "long-term maintained"]
DOMAIN_INTENSITIES = ["none", "low", "medium", "high"]
KNOWN_PACKS = [
    "web_app",
    "python_desktop",
    "c_embedded",
    "backend_service",
    "cli_library",
    "data_ml",
]

SECTION_ALIASES = {
    "project name": "project_name",
    "short description": "short_description",
    "repository / workspace": "repository",
    "main stakeholders": "stakeholders",
    "problem to solve": "problem_to_solve",
    "target outcome": "target_outcome",
    "why now": "why_now",
    "primary users": "primary_users",
    "secondary users": "secondary_users",
    "operational context": "operational_context",
    "main usage scenarios": "usage_scenarios",
    "in scope": "in_scope",
    "out of scope": "out_of_scope",
    "type": "project_type",
    "lifecycle": "lifecycle",
    "delivery mode": "delivery_mode",
    "criticality": "criticality",
    "domain intensity": "domain_intensity",
    "language / runtime constraints": "language_constraints",
    "platform / os constraints": "platform_constraints",
    "hardware constraints": "hardware_constraints",
    "performance / timing constraints": "performance_constraints",
    "security / privacy constraints": "security_constraints",
    "regulatory / safety constraints": "regulatory_constraints",
    "budget / team / maintenance constraints": "team_constraints",
    "external apis / services": "external_interfaces",
    "hardware / fieldbus / devices": "hardware_interfaces",
    "files / databases / protocols": "data_interfaces",
    "existing codebase or repository context": "existing_codebase",
    "suggested packs": "suggested_packs",
    "why these packs are relevant": "pack_rationale",
    "main unknowns": "unknowns",
    "main risks": "risks",
    "open questions to resolve before implementation": "open_questions",
    "existing notes / mails / chats": "notes_sources",
    "reference documents": "reference_documents",
    "related repositories": "related_repositories",
}

KEYWORD_PACK_RULES = {
    "data_ml": ["machine learning", "dataset", "training", "inference", "pytorch", "tensorflow", "scikit", "xgboost", "llm"],
    "web_app": ["browser", "frontend", "dashboard", "react", "vue", "angular", "next.js", "svelte"],
    "backend_service": ["rest api", "grpc", "backend service", "microservice", "server"],
    "python_desktop": ["pyqt", "pyside", "desktop", "gui", "qt", "tkinter"],
    "c_embedded": ["stm32", "embedded", "firmware", "rtos", "microcontroller", "bare metal", "modbus", "spi", "i2c"],
    "cli_library": ["command line", "sdk"],
}


@dataclass
class ProjectData:
    project_name: str = ""
    short_description: str = ""
    repository: str = ""
    stakeholders: str = ""
    problem_to_solve: str = ""
    target_outcome: str = ""
    why_now: str = ""
    primary_users: str = ""
    secondary_users: str = ""
    operational_context: str = ""
    usage_scenarios: str = ""
    in_scope: str = ""
    out_of_scope: str = ""
    project_type: str = ""
    lifecycle: str = ""
    delivery_mode: str = ""
    criticality: str = ""
    domain_intensity: str = ""
    language_constraints: str = ""
    platform_constraints: str = ""
    hardware_constraints: str = ""
    performance_constraints: str = ""
    security_constraints: str = ""
    regulatory_constraints: str = ""
    team_constraints: str = ""
    external_interfaces: str = ""
    hardware_interfaces: str = ""
    data_interfaces: str = ""
    existing_codebase: str = ""
    suggested_packs: str = ""
    pack_rationale: str = ""
    unknowns: str = ""
    risks: str = ""
    open_questions: str = ""
    notes_sources: str = ""
    reference_documents: str = ""
    related_repositories: str = ""
    derived_packs: List[str] = field(default_factory=list)

    def combined_text(self) -> str:
        fields = [getattr(self, name) for name in self.__dataclass_fields__ if isinstance(getattr(self, name), str)]
        return " ".join(fields).lower()


def normalize_choice(value: str, allowed: List[str], default: str = "") -> str:
    value = (value or "").strip().lower()
    if not value:
        return default
    for item in allowed:
        if value == item.lower():
            return item
    return default or value


def ask(prompt: str, default: str = "", allowed: Optional[List[str]] = None) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        value = raw or default
        if allowed:
            normalized = normalize_choice(value, allowed)
            if normalized in allowed:
                return normalized
            print(f"Please choose one of: {', '.join(allowed)}")
            continue
        return value


def multiline_input(prompt: str) -> str:
    print(f"{prompt} (finish with a single line containing only '.')")
    lines: List[str] = []
    while True:
        line = input()
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def parse_structured_markdown(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    result: Dict[str, str] = {}
    current_key: Optional[str] = None
    buffer: List[str] = []

    heading_pattern = re.compile(r"^#{1,6}\s+(.*)$")
    bullet_key_pattern = re.compile(r"^-\s+([^:]+):\s*(.*)$")

    def flush() -> None:
        nonlocal current_key, buffer
        if current_key is not None:
            result[current_key] = "\n".join(buffer).strip()
        current_key = None
        buffer = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading_match = heading_pattern.match(line)
        bullet_match = bullet_key_pattern.match(line)

        if heading_match:
            flush()
            title = heading_match.group(1).strip().lower()
            current_key = SECTION_ALIASES.get(title)
            continue

        if bullet_match:
            maybe_key = bullet_match.group(1).strip().lower()
            mapped = SECTION_ALIASES.get(maybe_key)
            if mapped:
                flush()
                current_key = mapped
                first_value = bullet_match.group(2).strip()
                if first_value:
                    buffer.append(first_value)
                continue

        if current_key is not None:
            buffer.append(line)

    flush()
    return {k: v for k, v in result.items() if v and not v.startswith("<")}


def derive_packs(data: ProjectData) -> List[str]:
    packs: List[str] = []
    ptype = data.project_type
    text = ' '.join([
        data.short_description,
        data.problem_to_solve,
        data.target_outcome,
        data.operational_context,
        data.usage_scenarios,
        data.language_constraints,
        data.platform_constraints,
        data.hardware_constraints,
        data.external_interfaces,
        data.hardware_interfaces,
        data.data_interfaces,
        data.existing_codebase,
    ]).lower()

    if ptype == "web_app":
        packs.append("web_app")
        if "api" in text or "backend" in text:
            packs.append("backend_service")
    elif ptype == "backend_service":
        packs.append("backend_service")
    elif ptype in {"desktop_app", "python_tool"} and any(token in text for token in KEYWORD_PACK_RULES["python_desktop"]):
        packs.append("python_desktop")
    elif ptype == "desktop_app":
        packs.append("python_desktop")
    elif ptype == "c_embedded":
        packs.append("c_embedded")
    elif ptype in {"cli", "library"}:
        packs.append("cli_library")

    for pack, keywords in KEYWORD_PACK_RULES.items():
        if pack == "cli_library" and ptype not in {"cli", "library", "mixed"}:
            continue
        if pack == "backend_service" and ptype not in {"backend_service", "web_app", "mixed"}:
            continue
        if any(keyword in text for keyword in keywords):
            packs.append(pack)

    ordered_unique: List[str] = []
    for pack in packs:
        if pack not in ordered_unique:
            ordered_unique.append(pack)
    return ordered_unique


def build_pack_rationale(data: ProjectData, packs: List[str]) -> str:
    reasons: List[str] = []
    text = data.combined_text()
    for pack in packs:
        if pack == "web_app":
            reasons.append("- `web_app`: browser-facing UI or dashboard concerns are present.")
        elif pack == "backend_service":
            reasons.append("- `backend_service`: service/API/integration concerns are present.")
        elif pack == "python_desktop":
            reasons.append("- `python_desktop`: desktop GUI / Qt / operator tool concerns are present.")
        elif pack == "c_embedded":
            reasons.append("- `c_embedded`: firmware, MCU, fieldbus, or hardware timing concerns are present.")
        elif pack == "cli_library":
            reasons.append("- `cli_library`: command-line or reusable library concerns are present.")
        elif pack == "data_ml":
            reasons.append("- `data_ml`: model, dataset, or training/inference concerns are present.")
    if not reasons and data.project_type == "mixed":
        reasons.append("- `mixed`: no single default pack dominates; choose packs manually.")
    if not reasons and "gui" in text:
        reasons.append("- `python_desktop`: inferred from GUI/operator wording.")
    return "\n".join(reasons) if reasons else "- No pack strongly inferred automatically; review manually."


def collect_interactively() -> ProjectData:
    data = ProjectData()
    data.project_name = ask("Project name")
    data.short_description = ask("Short description")
    data.repository = ask("Repository / workspace")
    data.stakeholders = ask("Main stakeholders")
    data.problem_to_solve = multiline_input("Problem to solve")
    data.target_outcome = multiline_input("Target outcome")
    data.why_now = ask("Why now")
    data.primary_users = ask("Primary users")
    data.secondary_users = ask("Secondary users")
    data.operational_context = multiline_input("Operational context")
    data.usage_scenarios = multiline_input("Main usage scenarios")
    data.in_scope = multiline_input("In scope")
    data.out_of_scope = multiline_input("Out of scope")
    data.project_type = ask("Project type", allowed=PROJECT_TYPES)
    data.lifecycle = ask("Lifecycle", default="greenfield", allowed=LIFECYCLES)
    data.delivery_mode = ask("Delivery mode", default="prototype", allowed=DELIVERY_MODES)
    data.criticality = ask("Criticality", default="medium", allowed=CRITICALITIES)
    data.domain_intensity = ask("Domain intensity", default="low", allowed=DOMAIN_INTENSITIES)
    data.language_constraints = multiline_input("Language / runtime constraints")
    data.platform_constraints = multiline_input("Platform / OS constraints")
    data.hardware_constraints = multiline_input("Hardware constraints")
    data.performance_constraints = multiline_input("Performance / timing constraints")
    data.security_constraints = multiline_input("Security / privacy constraints")
    data.regulatory_constraints = multiline_input("Regulatory / safety constraints")
    data.team_constraints = multiline_input("Budget / team / maintenance constraints")
    data.external_interfaces = multiline_input("External APIs / services")
    data.hardware_interfaces = multiline_input("Hardware / fieldbus / devices")
    data.data_interfaces = multiline_input("Files / databases / protocols")
    data.existing_codebase = multiline_input("Existing codebase or repository context")
    data.unknowns = multiline_input("Main unknowns")
    data.risks = multiline_input("Main risks")
    data.open_questions = multiline_input("Open questions to resolve before implementation")
    data.notes_sources = multiline_input("Existing notes / mails / chats")
    data.reference_documents = multiline_input("Reference documents")
    data.related_repositories = multiline_input("Related repositories")
    return data


def apply_parsed_values(parsed: Dict[str, str]) -> ProjectData:
    data = ProjectData()
    for key, value in parsed.items():
        if hasattr(data, key):
            setattr(data, key, value.strip())
    data.project_type = normalize_choice(data.project_type, PROJECT_TYPES, default="mixed")
    data.lifecycle = normalize_choice(data.lifecycle, LIFECYCLES, default="greenfield")
    data.delivery_mode = normalize_choice(data.delivery_mode, DELIVERY_MODES, default="prototype")
    data.criticality = normalize_choice(data.criticality, CRITICALITIES, default="medium")
    data.domain_intensity = normalize_choice(data.domain_intensity, DOMAIN_INTENSITIES, default="low")
    return data


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def bulletize(text: str) -> str:
    text = text.strip()
    if not text:
        return "- "
    lines = [line.strip("- ").rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(f"- {line}" for line in lines)


def md_project_intake(data: ProjectData) -> str:
    return f"""# Project Intake

> Generated by `tools/project_intake_wizard/wizard.py`

## Project identity
- Project name: {data.project_name}
- Short description: {data.short_description}
- Repository / workspace: {data.repository}
- Main stakeholders: {data.stakeholders}

## Problem and objective
### Problem to solve
{bulletize(data.problem_to_solve)}

### Target outcome
{bulletize(data.target_outcome)}

### Why now
{bulletize(data.why_now)}

## Users and usage context
- Primary users: {data.primary_users}
- Secondary users: {data.secondary_users}

### Operational context
{bulletize(data.operational_context)}

### Main usage scenarios
{bulletize(data.usage_scenarios)}

## Scope
### In scope
{bulletize(data.in_scope)}

### Out of scope
{bulletize(data.out_of_scope)}

## Project type and lifecycle
- Type: {data.project_type}
- Lifecycle: {data.lifecycle}
- Delivery mode: {data.delivery_mode}
- Criticality: {data.criticality}
- Domain intensity: {data.domain_intensity}

## Constraints
### Language / runtime constraints
{bulletize(data.language_constraints)}

### Platform / OS constraints
{bulletize(data.platform_constraints)}

### Hardware constraints
{bulletize(data.hardware_constraints)}

### Performance / timing constraints
{bulletize(data.performance_constraints)}

### Security / privacy constraints
{bulletize(data.security_constraints)}

### Regulatory / safety constraints
{bulletize(data.regulatory_constraints)}

### Budget / team / maintenance constraints
{bulletize(data.team_constraints)}

## Interfaces and dependencies
### External APIs / services
{bulletize(data.external_interfaces)}

### Hardware / fieldbus / devices
{bulletize(data.hardware_interfaces)}

### Files / databases / protocols
{bulletize(data.data_interfaces)}

### Existing codebase or repository context
{bulletize(data.existing_codebase)}

## Candidate packs
- Suggested packs: {', '.join(data.derived_packs) if data.derived_packs else 'none automatically suggested'}

### Why these packs are relevant
{data.pack_rationale}

## Unknowns and risks
### Main unknowns
{bulletize(data.unknowns)}

### Main risks
{bulletize(data.risks)}

### Open questions to resolve before implementation
{bulletize(data.open_questions)}

## Source material
### Existing notes / mails / chats
{bulletize(data.notes_sources)}

### Reference documents
{bulletize(data.reference_documents)}

### Related repositories
{bulletize(data.related_repositories)}
"""


def md_project_profile(data: ProjectData) -> str:
    pack_flags = {pack: ("yes" if pack in data.derived_packs else "no") for pack in KNOWN_PACKS}
    return f"""# Project Profile

> Generated by `tools/project_intake_wizard/wizard.py` — review and refine this file inside the project PRD.

**Status:** Draft
**Owner:** <your name>
**Last updated:** YYYY-MM-DD

## Project identity
- Project name: {data.project_name}
- Short description: {data.short_description}
- Repository / workspace: {data.repository}
- Main stakeholders: {data.stakeholders}

## Project family
- Type: `{data.project_type or 'mixed'}`
- Lifecycle: `{data.lifecycle or 'greenfield'}`
- Criticality: `{data.criticality or 'medium'}`
- Delivery mode: `{data.delivery_mode or 'prototype'}`

## Domain intensity
- {data.domain_intensity or 'low'}
- if medium or high, fill `06_domain/` before asking Codex to implement domain-heavy features

## Selected packs
List the packs intentionally selected for import into the project PRD.
- Core only: `{'yes' if not data.derived_packs else 'no'}`
- `packs/web_app`: `{pack_flags['web_app']}`
- `packs/python_desktop`: `{pack_flags['python_desktop']}`
- `packs/c_embedded`: `{pack_flags['c_embedded']}`
- `packs/backend_service`: `{pack_flags['backend_service']}`
- `packs/cli_library`: `{pack_flags['cli_library']}`
- `packs/data_ml`: `{pack_flags['data_ml']}`
- Other custom pack: `<name or n/a>`

## Target environment
- Platforms / OS: {data.platform_constraints or '<fill>'}
- Runtime / language: {data.language_constraints or '<fill>'}
- Hardware context: {data.hardware_constraints or '<fill>'}
- Deployment model: {data.delivery_mode or '<fill>'}
- Offline / online expectations: <fill>

## Key constraints
- Budget / team / maintenance constraints: {data.team_constraints or '<fill>'}
- Performance / timing constraints: {data.performance_constraints or '<fill>'}
- Security / privacy constraints: {data.security_constraints or '<fill>'}
- Regulatory / safety constraints: {data.regulatory_constraints or '<fill>'}

## Project-specific notes
- Why this pack selection is appropriate:
{data.pack_rationale}
- What is intentionally out of scope for this project:
{bulletize(data.out_of_scope)}
- Which documents should be treated as priority entry points:
  - `PROJECT_INTAKE.md`
  - `PROJECT_PROFILE.md`
  - `01_product/product_brief.md`
  - `04_requirements/requirements_catalog.md`
"""


def pack_reason_line(data: ProjectData, pack: str) -> str:
    if pack == "python_desktop":
        return "desktop or GUI cues were found in the intake"
    if pack == "web_app":
        return "web or frontend cues were found in the intake"
    if pack == "backend_service":
        return "API or service cues were found in the intake"
    if pack == "c_embedded":
        return "embedded, firmware, hardware, or fieldbus cues were found in the intake"
    if pack == "cli_library":
        return "CLI or library reuse cues were found in the intake"
    if pack == "data_ml":
        return "data or machine-learning cues were found in the intake"
    return "the intake suggests this pack may be useful"


def md_packs_active(data: ProjectData) -> str:
    if data.derived_packs:
        packs_list = "\n\n".join(
            f"### PACK_{pack.upper()}\n"
            f"- Status: `proposed`\n"
            f"- Version: `n/a`\n"
            f"- Source library path: `prd_library/packs/{pack}/`\n"
            f"- Imported into project path: `40_active_packs/{pack}/`\n"
            f"- Imported files:\n"
            f"  - `<review after import>`\n"
            f"- Why it applies to this project: {pack_reason_line(data, pack)}\n"
            f"- Required impacts on core docs:\n"
            f"  - `04_requirements/...`\n"
            f"  - `10_architecture/...`\n"
            f"  - `30_feature/...`\n"
            f"  - `90_quality/...`\n"
            f"- Local adaptations after import: `<none yet>`\n"
            f"- Open questions: `<review before activation>`"
            for pack in data.derived_packs
        )
    else:
        packs_list = "### PACK_CORE_ONLY\n- Status: `active`\n- Version: `n/a`\n- Source library path: `prd_library/core/`\n- Imported into project path: `./`\n- Imported files:\n  - `core/`\n- Why it applies to this project: no additional pack was strongly inferred from the intake.\n- Required impacts on core docs:\n  - `<none beyond normal PRD completion>`\n- Local adaptations after import: `<n/a>`\n- Open questions: `<review manually if the project grows>`"
    return f"""# Packs Active

> Generated by `tools/project_intake_wizard/wizard.py`.

## Purpose
This file is the pack manifest for the current project PRD.
The wizard fills it with a first recommendation only.

## Current recommendation from intake
{packs_list}

## Reminder
Suggested packs are not automatically active.
After importing a pack into `40_active_packs/`, review this file and switch the relevant entries from `proposed` to `active`.
"""


def md_next_steps(data: ProjectData) -> str:
    questions: List[str] = []
    if not data.project_name:
        questions.append("- Confirm the final project name.")
    if not data.problem_to_solve:
        questions.append("- Clarify the concrete problem to solve.")
    if not data.target_outcome:
        questions.append("- Define the target deliverable or operational outcome.")
    if not data.primary_users:
        questions.append("- Identify the primary users or operators.")
    if not data.in_scope:
        questions.append("- Define what is explicitly in scope for the first delivery.")
    if not data.out_of_scope:
        questions.append("- Define what is explicitly out of scope.")
    if not data.existing_codebase:
        questions.append("- State whether the project is greenfield or constrained by an existing repository/codebase.")
    if not data.derived_packs:
        questions.append("- Review pack selection manually; no strong automatic recommendation was inferred.")
    if data.domain_intensity in {"medium", "high"}:
        questions.append("- Fill `06_domain/` before implementation-oriented prompts.")
    questions_block = "\n".join(questions) if questions else "- Intake is already good enough for a first GPT pass."

    return f"""# Next Steps for GPT

## Recommended immediate workflow
1. Read `PROJECT_INTAKE.md`.
2. Read `PROJECT_PROFILE.md`.
3. Review `PACKS_ACTIVE.md` and confirm pack choices.
4. Read the PRD core template (`START_HERE.md`, `PRD.md`, `PRD_READY_CHECKLIST.md`).
5. Ask only the missing questions that block a clean initial PRD.
6. Pre-fill the PRD with the information already captured.

## Suggested GPT prompt
```text
Read `PROJECT_INTAKE.md`, `PROJECT_PROFILE.md`, and `PACKS_ACTIVE.md`.
Then read the PRD template.
Identify what is already known, what is missing, and which missing answers are really necessary.
Ask a compact list of blocking questions only.
Then propose an initial fill of the PRD structure.
```

## Missing or weak areas detected by the wizard
{questions_block}

## Recommended pack candidates
- {', '.join(data.derived_packs) if data.derived_packs else 'none automatically suggested'}
"""


def generate_outputs(data: ProjectData, output_dir: Path) -> None:
    data.derived_packs = derive_packs(data)
    data.pack_rationale = build_pack_rationale(data, data.derived_packs)
    write_text(output_dir / "PROJECT_INTAKE.md", md_project_intake(data))
    write_text(output_dir / "PROJECT_PROFILE.md", md_project_profile(data))
    write_text(output_dir / "PACKS_ACTIVE.md", md_packs_active(data))
    write_text(output_dir / "NEXT_STEPS_FOR_GPT.md", md_next_steps(data))


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate initial PRD intake files from a wizard or a structured brief.")
    parser.add_argument("--mode", choices=["interactive", "brief"], required=True, help="Data entry mode")
    parser.add_argument("--input-file", type=Path, help="Structured markdown brief file used in brief mode")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory where generated files will be written")
    return parser


def main() -> int:
    parser = build_argparser()
    args = parser.parse_args()

    if args.mode == "interactive":
        data = collect_interactively()
    else:
        if not args.input_file:
            parser.error("--input-file is required in brief mode")
        parsed = parse_structured_markdown(args.input_file)
        if not parsed:
            print("The input brief did not yield any structured data. Use the provided template headings.", file=sys.stderr)
            return 2
        data = apply_parsed_values(parsed)

    generate_outputs(data, args.output_dir)
    print(f"Generated intake files in: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
