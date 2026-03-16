# Main flows

> **PRD Policy:** **PROJECT (editable)** — Describe the principal user and data flows through the system.  Understanding flows helps developers implement consistent logic and identify corner cases.

**Last updated:** 2026‑03‑16

## User flow: Start and listen

1. **Launch:** User starts the RSPdx application.  The configuration is loaded, and the device controller initialises the RSPdx hardware.  If no device is detected, the user is notified and the application enters a demo mode.
2. **Create receiver:** The user clicks “+” to add a new receiver.  A new receiver tab appears with default parameters (frequency, demodulator and bandwidth).
3. **Tune & configure:** The user sets the centre frequency and bandwidth using dials or text boxes.  The pipeline manager updates the mixer and filters accordingly.
4. **Select demodulator:** The user chooses a demodulation mode (FM/AM/CW/USB/LSB or a plugin).  If a plugin is selected, the plugin manager loads it and registers its processing functions with the receiver.
5. **View spectrum:** The spectrum and waterfall plots update in real time based on the incoming IQ stream and receiver settings.
6. **Listen:** Demodulated audio is sent to the system audio output.  The user can adjust volume, record audio or send it to an external sink.
7. **Manage plugins:** The user can open the plugin manager panel, enable/disable plugins, update plugin settings or load new plugin files.
8. **Remove receiver:** When finished, the user closes the receiver tab.  The pipeline manager stops processing for that receiver and frees resources.
9. **Exit:** On quitting the application, the device controller stops the SDR, the ThreadManager stops all threads, and logs are flushed.

## Developer flow: Adding a plugin

1. **Create plugin skeleton:** Developer copies the example plugin template and fills in metadata (name, version, capabilities) and life‑cycle functions (`init`, `process`, `destroy`).
2. **Implement processing:** The plugin code receives IQ data (or demodulated symbols) via the API.  It performs demodulation or analysis and returns audio samples or structured data.
3. **Build & package:** The plugin is compiled (if native) or bundled (if Python) into the expected format (shared library `.so`/`.dll` or `.py` module) and placed in the plugin directory.
4. **Load plugin:** The plugin manager scans the plugin directory, discovers the new plugin, loads it and registers it.  Errors during load are logged and surfaced to the user.
5. **Test plugin:** The developer creates a receiver in the UI, selects the new plugin and tests it with known signals.  Adjustments are made until demodulation works as expected.

## Data flow: Pipeline processing

1. **Acquisition:** The device controller receives a continuous IQ stream from the SDR hardware and writes it into a ring buffer.
2. **Dispatch:** The pipeline manager reads chunks of IQ data and dispatches them to each active receiver.  Each receiver may operate at a different centre frequency using digital down‑conversion.
3. **Filtering & decimation:** Each receiver mixes the signal to baseband, applies a bandpass filter, and decimates to the target sample rate.  Filters are designed using C/C++ libraries for efficiency.
4. **Demodulation:** The processed IQ stream is passed to the selected demodulator (either built‑in or plugin).  Demodulators may produce audio samples, bit streams or other outputs.
5. **Analysis (optional):** Any active analysis plugin receives data from the demodulator and performs further processing (e.g. cryptanalysis).  It may feed back into the UI or generate logs.
6. **Data storage:** Spectrum and waterfall data are computed using FFTs and stored in data buffers.  Quality metrics (e.g. error vector magnitude) are updated.
7. **Rendering & output:** The UI reads the spectrum and waterfall buffers at its own pace and updates plots.  Audio output threads send demodulated samples to the sound card.

## Acceptance criteria

- The flows reflect the implemented system and are updated when workflows change.
- Both user and developer flows are validated by walkthroughs and test cases.