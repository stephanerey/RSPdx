# Pack Selection Guide

## Goal
Help choose the smallest useful set of packs for a project.

## Selection principles
- Start from the core only.
- Add a pack only when it changes requirements, architecture, validation, or delivery constraints in a meaningful way.
- Prefer one or two relevant packs over many weakly relevant packs.

## Typical pack choices
### Web platform
- `web_app`
- optionally `backend_service`

### Python GUI / instrument control
- `python_desktop`
- optionally `c_embedded` if there is a companion firmware or hardware board

### Firmware / MCU / RTOS
- `c_embedded`

### API service / daemon / worker
- `backend_service`

### CLI or reusable library
- `cli_library`

### Data processing / ML / training pipeline
- `data_ml`

## Warning signs of over-selection
- the same topic appears in multiple packs with different wording
- the project team cannot explain why a pack is active
- the pack adds no requirements or validation consequences
