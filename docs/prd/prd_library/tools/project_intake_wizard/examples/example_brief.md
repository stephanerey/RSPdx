# Structured Project Brief

## Project name
Antrack

## Short description
PyQt5 desktop application used to track an antenna system, coordinate external instruments, and manage operational scans.

## Repository / workspace
C:/Projects/Antrack

## Main stakeholders
RF engineer, antenna operator, future maintainers

## Problem to solve
The current codebase needs a cleaner project framing so the PRD can be generated consistently and Codex can work from a compact and correct context.

## Target outcome
A structured project PRD plus the right pack overlays for a Python desktop tool that interacts with hardware and long-running workflows.

## Why now
The codebase is growing and the cost of implicit knowledge is increasing.

## Primary users
Operator and developer

## Secondary users
Future maintainers

## Operational context
Desktop engineering tool used near hardware setups, with long-running measurements, tracking loops, and instrument coordination.

## Main usage scenarios
Configure tracking.
Run scans.
Monitor status.
Collect logs and measurement context.

## In scope
Desktop GUI.
Threaded or async task orchestration.
Instrument communication.
Project structure and maintainability.

## Out of scope
Web frontend.
Cloud-native multi-tenant backend.

## Type
desktop_app

## Lifecycle
refactor

## Delivery mode
long-term maintained

## Criticality
high

## Domain intensity
medium

## Language / runtime constraints
Python 3.11, PyQt5, PyQtGraph.

## Platform / OS constraints
Windows primary, Linux possible later.

## Hardware constraints
Axis controller, motors, encoders, possible power meter, TCP-connected instruments.

## Performance / timing constraints
Responsive GUI and robust handling of long-running tasks.

## Security / privacy constraints
Internal engineering tool, moderate concerns.

## Regulatory / safety constraints
Do not produce unsafe motion commands or hide interlock-relevant states.

## Budget / team / maintenance constraints
Single main developer for now, future maintainers must understand the structure quickly.

## External APIs / services
Possibly ephemeris, local services, instrument TCP APIs.

## Hardware / fieldbus / devices
Antenna controller, motor drivers, encoders, instruments.

## Files / databases / protocols
TCP, CSV, logs, configuration files.

## Existing codebase or repository context
Existing repository under refactor with GUI, worker logic, and hardware interfaces already present.

## Main unknowns
Final concurrency model and how far domain docs should go.

## Main risks
Wrong abstraction around tracking and scan workflows, fragile threading model, hidden business logic.

## Open questions to resolve before implementation
What belongs in the domain layer versus implementation notes? Which packs should be considered mandatory?

## Existing notes / mails / chats
Engineering notes and previous chat history.

## Reference documents
PRD library, design notes, protocol docs.

## Related repositories
Antrack main repo
