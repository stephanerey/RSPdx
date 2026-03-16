# Architecture overview

> **PRD Policy:** **PROJECT (editable)** — Describe the high‑level architecture, major components and their interactions.  This overview guides developers and informs future design decisions.

**Last updated:** 2026‑03‑16

## Summary

RSPdx is built as a modular SDR application with clear separation of concerns.  The system is divided into components that interact via well‑defined interfaces and are orchestrated by a central pipeline manager.  The architecture draws inspiration from SDR++ but is implemented primarily in Python with performance‑critical sections offloaded to C/C++ libraries.

## Major components

| Component | Responsibility | Notes |
|---|---|---|
| **Device controller** | Manages SDR hardware via SoapySDR/SDRplay API: device enumeration, sample rate, gain and frequency settings; streams IQ samples to the pipeline manager. | Encapsulates vendor specifics and allows future support for other devices. |
| **Pipeline manager** | Coordinates the flow of IQ data through demodulation and analysis stages.  It dispatches samples to active receivers and plugins, applies filters and rate conversions, and manages threading. | Implements the “data bus” pattern; ensures thread safety and low latency. |
| **ThreadManager** | Provides a framework for starting, stopping and monitoring worker threads and async tasks.  Integrates the UI panel showing thread statistics from the Antrack project. | Ensures controlled lifecycle of DSP and UI tasks; surfaces errors and performance metrics. |
| **Plugin manager** | Loads, initialises and manages demodulator and analysis plugins via a defined API.  Handles versioning, capabilities discovery and registration with the pipeline. | Supports loading plugins written in C/C++ or Python; isolates plugin failures from the core. |
| **Receivers** | Logical entities representing sub‑bands.  Each receiver contains a demodulator (analog or digital) and associated filters; outputs audio or data. | Users can spawn multiple receivers on different frequencies. |
| **Data storage & metrics** | Buffers spectral data, waterfall frames, constellation points and quality metrics; exposes this data to the UI. | Uses ring buffers and efficient Numpy structures. |
| **Audio output** | Collects demodulated audio and sends it to the system audio device.  Provides audio buffering, volume control and optional recording. | Uses `sounddevice` (PortAudio) or platform‑specific audio APIs. |
| **User interface (UI)** | Provides a PyQt/PyQtGraph based GUI with multiple panels: frequency/bandwidth controls, spectrum/waterfall plots, receiver list, plugin manager and thread statistics. | Designed for responsiveness and clarity; uses signals/slots and model‑view separation. |

## Layering and dependencies

The architecture follows these layering rules:

1. **Core layer:** Contains the device controller, pipeline manager, ThreadManager and plugin manager.  No direct imports from the UI.  Implements all signal processing, data handling and threading.
2. **UI layer:** Implements presentation and user interaction.  Communicates with the core via signals/slots and model objects.  Must not perform heavy DSP; instead subscribes to updates and commands.
3. **Plugins:** Implement demodulators or analysis modules.  They depend on the plugin API but not on the UI.  Plugins can be native or Python modules; they are loaded by the plugin manager and operate on IQ buffers or intermediate data.

This separation allows independent development and testing of each layer and paves the way for headless or remote control in the future.

## Data flow

1. **Acquisition:** The device controller acquires IQ samples from the SDRplay RSPdx and passes them to the pipeline manager.
2. **Processing:** The pipeline manager dispatches the IQ stream to all active receivers.  Each receiver mixes, filters and decimates the data, then hands it to its demodulator plugin.
3. **Demodulation:** Analog demodulators perform FM/AM/CW/USB/LSB extraction.  Digital demodulators decode symbol streams into audio or data.  Plugins may produce demodulated audio, bit streams or statistics.
4. **Analysis:** Optional cryptanalysis plugins perform additional processing on the demodulated or raw data (e.g. frequency hopping analysis, decoding support).  Results may be logged or fed back into the UI.
5. **Rendering:** Data storage buffers are updated with spectrum and waterfall information; the UI reads these buffers and renders plots.  Audio output sends demodulated audio to the speaker.

## Non‑goals

- Running on embedded microcontrollers or mobile devices; the target platforms are desktop PCs (Windows/Linux).
- Providing transmit (TX) capabilities or acting as a transceiver.
- Implementing machine‑learning‑based demodulation in this phase.

## Acceptance criteria

- The architecture document reflects the current design and is kept up to date as new components are added.
- Each component has a clear interface and minimal coupling to others; tests cover interactions.
- Changes to the DSP pipeline or plugin API do not require changes in the UI layer.