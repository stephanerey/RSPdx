# Open questions

> **PRD Policy:** **PROJECT (editable)** — Track unresolved questions that require clarification before implementation.  Each question should have an owner responsible for finding the answer.

**Last updated:** 2026‑03‑16

| QID | Question | Owner | Desired answer by | Notes |
|---|---|---|---|---|
| **Q‑001** | Which digital demodulation modes should be prioritised after the MVP (e.g. TETRA, DMR, P25, POCSAG)? | Stéphane | 2026‑04‑10 | Influences design of plugin API and phase P40 scope. |
| **Q‑002** | What is the expected plugin API surface (C vs Python, synchronisation semantics, memory management)? | Architecture lead | 2026‑04‑15 | Detailed in architecture definitions; resolves D‑003 alternatives. |
| **Q‑003** | How will the cryptanalysis modules access and process IQ or demodulated data?  Are there legal constraints on distribution? | Legal/tech consultant | 2026‑05‑15 | Determine feasibility and constraints for P50. |
| **Q‑004** | What user interface style is preferred (single‑window vs multiple panels, dark/light theme, docking)? | UI/UX designer | 2026‑03‑31 | Guides the UI implementation in P30. |
| **Q‑005** | Do we need remote/network control (e.g. headless server with GUI client)? | Product owner | 2026‑04‑30 | Could influence architecture (client‑server separation) and roadmap. |
| **Q‑006** | Should we package the application with PyInstaller, Conda or Docker; how will we handle native dependencies on Windows and Linux? | DevOps | 2026‑06‑01 | Affects P60 packaging tasks. |

Unanswered questions should be revisited regularly.  Once answered, update the relevant sections of the PRD and remove or archive the question.