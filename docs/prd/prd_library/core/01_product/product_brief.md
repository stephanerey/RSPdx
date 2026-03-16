# Product Brief

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026‑03‑16

## Problem statement

The existing RSPdx application is a monolithic prototype that couples the user interface, SDR hardware access and digital signal processing in one code base.  It supports only a limited set of modes and lacks a clear pathway to extend its capabilities.  The goal of this project is to **refactor and modernise the RSPdx software into a modular, high‑performance SDR receiver**.  The new application must:

- Provide reliable audio reception for analog modes (FM, AM, CW, USB, LSB) on the SDRplay RSPdx device.
- Offer a **plugin framework** that allows independent development and integration of new digital demodulators and cryptanalysis modules.
- Achieve low latency and efficient CPU utilisation through strategic use of C/C++ libraries for heavy DSP tasks while keeping orchestration and UI in Python.
- Expose a clean, intuitive user interface with multi‑receiver support and real‑time visualisation (spectra, waterfall, constellation).

This project will transform the RSPdx codebase into a maintainable platform capable of supporting future research and experimentation in SDR demodulation and signal analysis.

## Target users / personas

- **Radio amateur experimenter (Persona A):** hobbyist and club member who wants to explore radio bands, decode analog signals and try out new digital modes without needing to compile C++ code.
- **Electronics/ RF engineer (Persona B):** professional engineer (e.g. at CERN) who uses SDR receivers for instrumentation, monitoring and prototyping.  Needs a reliable, extendable tool with clear APIs for integrating custom demodulators and analysis routines.
- **Academic researcher (Persona C):** university or research‑lab user working on novel demodulation or cryptanalysis algorithms.  Requires a modular framework to plug in experimental code and evaluate performance.
- **Cybersecurity analyst / signals intelligence (Persona D):** analyst tasked with intercepting and analysing unknown digital transmissions.  Needs high‑performance demodulators and future cryptanalysis modules to gain insight into signal content.

## Goals

- **G1 – Analog demodulation:** Support high‑quality audio reception for FM, AM, CW, USB and LSB, with adjustable bandwidth and gain.
- **G2 – Extensible plugin architecture:** Define and implement a plugin API that allows loading demodulators (analog or digital) and analysis modules at runtime, inspired by the SDR++ model.  Provide example plugins as reference.
- **G3 – High performance:** Achieve low latency (<150 ms from sample to audio) and modest CPU usage (<50% on mid‑range hardware) through C/C++ DSP libraries (e.g. FFTW, SoapySDR, custom C filters) and efficient threading.
- **G4 – Intuitive user experience:** Provide a multi‑receiver GUI using PyQt/PyQtGraph with clear controls for frequency, sample rate, bandwidth, demodulator selection and plugin management.  Include visualisations (spectrum, waterfall, constellation) and thread statistics via the reused ThreadManager UI.
- **G5 – Cross‑platform and maintainable:** Ensure the application runs on Windows 10/11 and modern Linux distributions.  Maintain a clean, modular codebase with documented interfaces and automated tests.

## Non‑goals

- **Transmission (TX):** The application is receive‑only.  No support for transmitting or beacon functions is planned.
- **Full SDR++ parity:** We draw inspiration from SDR++’s plugin system but we do not aim to replicate all its features or UI design; RSPdx is a separate project focused on our hardware and use cases.
- **Machine‑learning demodulators:** There is no short‑term plan to integrate AI/ML demodulation techniques; research may occur in separate projects.
- **Embedded hardware control:** The project assumes the RSPdx device is controlled solely through the SoapySDR/SDRplay API.  No direct microcontroller firmware development is planned.

## Scope by phase

### MVP (P30)

- Integrate the ThreadManager from Antrack and refactor the existing RSPdx code into a modular structure (device controller, pipeline manager, plugin manager, UI).
- Implement the five analog demodulation modes (FM, AM, CW, USB, LSB) using high‑performance C/C++ DSP where appropriate.
- Build the multi‑receiver GUI with basic spectrum and waterfall displays, frequency/bandwidth controls and plugin manager panel.
- Define the plugin API and provide a skeleton example plugin.

### V2+

- Develop and integrate digital demodulation plugins (e.g. TETRA, DMR, P25) using the plugin framework.
- Introduce cryptanalysis modules for frequency‑hopping analysis, symbol‑stream decoding and integration with external decoders.
- Expand UI features: recording/ playback, bookmarking, advanced waterfall controls, remote/network control.
- Optimise performance and resource use; implement configuration profiles and auto‑tuning heuristics.
- Conduct portability testing (ARM platforms, macOS) and packaging (PyInstaller, Docker).

## Constraints

- **Hardware dependency:** The primary target hardware is the **SDRplay RSPdx** using the SoapySDR and SDRplay APIs.  The design must abstract hardware access but some DSP may be tuned to this device’s capabilities.
- **Technology stack:** The application is primarily written in **Python 3.10+** for orchestration and UI.  **C/C++ libraries** (FFTW, custom filters) will be used for heavy signal processing; appropriate bindings (CFFI, Cython or Pybind11) will be required.
- **Cross‑platform support:** Must run on 64‑bit Windows 10/11 and recent Linux distributions.  Platform‑specific differences (audio devices, driver installation) must be handled gracefully.
- **Licensing:** Only open‑source libraries with permissive licenses (MIT, BSD, Apache, LGPL) can be used.  SDRplay’s proprietary API may impose redistribution constraints.
- **Security & privacy:** No user data is collected; however, cryptanalysis modules may touch sensitive transmissions, so care must be taken to avoid storing or transmitting decoded content inadvertently.

## Success criteria

Success is measured against the KPIs defined in `kpis.md`.  The MVP is successful when the analog modes function reliably with low latency and CPU usage, the plugin framework can load a skeleton plugin, and the user interface is stable for multi‑receiver use.  V2+ success will include delivering at least one digital demodulation plugin, demonstrating cryptanalysis capability, and meeting the performance targets across supported platforms.