# Versioning and release policy

> **PRD Policy:** **PROJECT (editable)** — Define how versions are numbered and how releases are managed.  A clear policy simplifies dependency management and user expectations.

**Last updated:** 2026‑03‑16

## Versioning scheme

RSPdx follows **semantic versioning**: `MAJOR.MINOR.PATCH`.

- **MAJOR** versions introduce incompatible changes, major feature overhauls or new plugin API versions.  Upgrades may require developers to adjust their plugins or configurations.
- **MINOR** versions add backward‑compatible features, plugins and improvements.  Existing users can upgrade without changes.
- **PATCH** versions include bug fixes, performance improvements and documentation updates with no API changes.

Example: Version **1.2.3** denotes the third patch of the second minor release of the first major version.

## Release cadence

- **Pre‑release:** During early development (P00–P20), version numbers will include `0.x.y` to denote unstable releases.
- **MVP release:** The first stable release after completing P30 will be tagged `1.0.0`.
- **Minor releases:** After the MVP, new features (digital modes, cryptanalysis modules) will increment the minor version (e.g. `1.1.0`, `1.2.0`).  Expect 3–4 minor releases per year.
- **Patch releases:** Bug fixes and performance improvements will be released as needed; no fixed schedule.

## Compatibility policy

- **Backward compatibility:** Minor and patch releases must maintain compatibility with plugins built for the same major version.  The plugin API cannot be broken without a major version bump.
- **Deprecation:** When an API or feature is to be removed, deprecation notices will be added at least one minor release before removal.  Deprecated functions may emit warnings.
- **Forward compatibility:** Plugins may target a minimum supported version; they should gracefully degrade or refuse to load on older versions.

## Breaking changes

Breaking changes (e.g. removing a demodulation mode, altering plugin interfaces) require consensus from the project maintainers and must be documented.  Affected users and plugin developers should be notified via release notes.

## Release process

1. All code must pass automated tests and meet the KPIs.  Merge requests are peer‑reviewed.
2. A release candidate is tagged (e.g. `1.0.0‑rc1`) and shared with testers.  Bugs found at this stage are resolved before the final release.
3. The final version is tagged (e.g. `1.0.0`) and packaged for Windows and Linux (executable, installer or archive).  Checksums and signatures are provided.
4. Release notes summarise new features, bug fixes, deprecations, known issues and upgrade instructions.
5. The PRD is updated to reflect changes in requirements, architecture or KPIs since the last release.