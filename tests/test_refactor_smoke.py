import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PyQt5 import QtWidgets

from src.core.demodulators.am import demodulate_am
from src.core.demodulators.cw import demodulate_cw
from src.core.demodulators.registry import build_demodulator_registry
from src.core.demodulators.ssb import demodulate_ssb
from src.core.dsp import compute_power_spectrum_db, select_fft_size
from src.gui.gain_table_ui import AutoGainTableWidget
from src.gui.log_viewer_ui import LogViewerWidget
from src.gui.receiver_tab import (
    ReceiverTab,
    average_recent_noise_samples,
    integrate_band_noise_power,
    measure_band_noise,
)
from src.gui.threads_ui import ThreadsWidget
from src.threading_utils.thread_manager import ManagedTaskStatus, ThreadManager
from src.tools.gain_table import build_default_auto_gain_profiles, lna_attenuation_db
from src.tools.paths import ensure_runtime_directories, get_log_file_path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class RefactorSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_runtime_paths_are_available(self):
        directories = ensure_runtime_directories()
        self.assertTrue(directories["logs"].exists())
        self.assertEqual(get_log_file_path().parent, directories["logs"])

    def test_thread_manager_tracks_external_threads(self):
        manager = ThreadManager()
        manager.register_external_thread("unit-thread")
        diagnostics = manager.get_diagnostics()
        self.assertEqual(diagnostics["unit-thread"]["status"], "running")
        manager.unregister_external_thread("unit-thread", status=ManagedTaskStatus.FINISHED)
        diagnostics = manager.get_diagnostics()
        self.assertEqual(diagnostics["unit-thread"]["status"], "finished")

    def test_dsp_spectrum_helpers_return_consistent_shapes(self):
        fs = 2_000_000.0
        fft_size = select_fft_size(fs, 65_536)
        tone = np.exp(1j * 2.0 * np.pi * 0.05 * np.arange(fft_size, dtype=np.float32))
        spectrum = compute_power_spectrum_db(tone.astype(np.complex64), fft_size)
        self.assertEqual(spectrum.shape[0], fft_size)
        self.assertTrue(np.isfinite(spectrum).all())

    def test_block_demodulators_return_audio(self):
        n = np.arange(4096, dtype=np.float32)
        iq = np.exp(1j * 2.0 * np.pi * 0.01 * n).astype(np.complex64)

        am = demodulate_am(iq)
        usb = demodulate_ssb(iq, sideband="usb")
        cw = demodulate_cw(iq, tone_frequency_hz=700.0, sample_rate_hz=48_000.0)

        self.assertEqual(am.dtype, np.float32)
        self.assertEqual(usb.dtype, np.float32)
        self.assertEqual(cw.dtype, np.float32)
        self.assertGreater(am.size, 0)
        self.assertGreater(usb.size, 0)
        self.assertGreater(cw.size, 0)

    def test_demodulator_registry_exposes_expected_modes(self):
        registry = build_demodulator_registry()
        self.assertIn("fm", registry)
        self.assertIn("am", registry)
        self.assertIn("usb", registry)
        self.assertIn("lsb", registry)
        self.assertIn("cw", registry)

    def test_monitoring_widgets_instantiate(self):
        manager = ThreadManager()
        threads_widget = ThreadsWidget(manager)
        self.assertIsNotNone(threads_widget.table)
        self.assertIsNotNone(threads_widget.receiver_widget)

        threads_widget._on_perf_updated(
            {
                "iq_mbit_s": 127.5,
                "sample_rate_effective_hz": 1_992_000.0,
                "sample_rate_ratio_pct": 99.6,
                "block_rate_hz": 30.4,
                "fft_rate_hz": 10.0,
                "fft_avg_ms": 1.86,
                "time_outs": 0,
                "stream_errors": 0,
                "mode": "hardware",
                "fft_size": 65_536,
                "buffer_size": 65_536,
            }
        )
        threads_widget._on_receiver_perf_updated(
            {
                "name": "RX1",
                "demod_mode": "FM",
                "audio_enabled": False,
                "selected_freq_hz": 145_500_000.0,
                "bandwidth_hz": 25_000.0,
                "baseband_ksample_s": 48.0,
                "iq_block_rate_hz": 30.4,
                "process_avg_ms": 0.42,
                "audio_rms": 0.0,
                "audio_peak": 0.0,
                "audio_buffer_fill_pct": 0.0,
            }
        )
        self.assertEqual(threads_widget.receiver_widget.table.rowCount(), 1)

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = Path(tmp_dir) / "rspdx.log"
            log_file.write_text("hello\nworld\n", encoding="utf-8")
            log_widget = LogViewerWidget(log_file=log_file)
            log_widget.refresh()
            self.assertIn("hello", log_widget.text_edit.toPlainText())
            export_file = Path(tmp_dir) / "perf.csv"
            threads_widget.performance_widget.export_history_csv(str(export_file))
            self.assertTrue(export_file.exists())
            self.assertIn("iq_mbit_s", export_file.read_text(encoding="utf-8"))

        threads_widget._reset_perf_history()
        self.assertEqual(threads_widget.receiver_widget.table.rowCount(), 0)

        threads_widget.deleteLater()

    def test_receiver_tab_exposes_demodulator_buttons(self):
        widget = ReceiverTab()
        self.assertEqual(sorted(widget.demodButtons.keys()), ["am", "cw", "fm", "lsb", "usb"])
        self.assertFalse(widget.audioEnable.isChecked())
        self.assertEqual(widget.noiseValueLabel.text(), "--.-- dB")
        self.assertEqual(widget.noiseSpectrumLabel.text(), "--.-- dB/bin")
        self.assertEqual(widget.noiseReferenceButton.text(), "Show relative")
        self.assertAlmostEqual(widget.noiseAverageSpin.value(), 0.5, places=6)
        self.assertAlmostEqual(widget.noiseAverageSpin.singleStep(), 0.1, places=6)
        widget.deleteLater()

    def test_noise_button_toggles_between_absolute_and_relative(self):
        widget = ReceiverTab()
        widget._latest_noise_linear = 4.0
        widget._refresh_noise_measurement = widget._update_noise_mode_ui

        widget._toggle_noise_mode()
        self.assertTrue(widget._noise_relative_enabled)
        self.assertAlmostEqual(widget._noise_reference_linear, 4.0, places=9)
        self.assertEqual(widget.noiseModeLabel.text(), "Relative")
        self.assertEqual(widget.noiseReferenceButton.text(), "Show absolute")

        widget._toggle_noise_mode()
        self.assertFalse(widget._noise_relative_enabled)
        self.assertEqual(widget.noiseModeLabel.text(), "Absolute")
        self.assertEqual(widget.noiseReferenceButton.text(), "Show relative")
        widget.deleteLater()

    def test_integrate_band_noise_power_sums_only_bins_inside_band(self):
        freqs = np.array([99.0, 99.5, 100.0, 100.5, 101.0], dtype=np.float64) * 1e6
        power_db = np.array([-30.0, -20.0, -10.0, -20.0, -30.0], dtype=np.float32)

        result = integrate_band_noise_power(freqs, power_db, 100.0e6, 1.0e6)

        self.assertIsNotNone(result)
        integrated_linear, integrated_db = result
        expected_linear = (10.0 ** (-20.0 / 10.0)) + (10.0 ** (-10.0 / 10.0)) + (10.0 ** (-20.0 / 10.0))
        self.assertAlmostEqual(integrated_linear, expected_linear, places=9)
        self.assertAlmostEqual(integrated_db, 10.0 * np.log10(expected_linear), places=6)

    def test_measure_band_noise_reports_integrated_and_per_bin_levels(self):
        freqs = np.array([99.0, 99.5, 100.0, 100.5, 101.0], dtype=np.float64) * 1e6
        power_db = np.array([-30.0, -20.0, -10.0, -20.0, -30.0], dtype=np.float32)

        result = measure_band_noise(freqs, power_db, 100.0e6, 1.0e6)

        self.assertIsNotNone(result)
        assert result is not None
        expected_linear = (10.0 ** (-20.0 / 10.0)) + (10.0 ** (-10.0 / 10.0)) + (10.0 ** (-20.0 / 10.0))
        expected_mean_bin = expected_linear / 3.0
        self.assertEqual(result["bins_count"], 3)
        self.assertAlmostEqual(result["integrated_linear"], expected_linear, places=9)
        self.assertAlmostEqual(result["integrated_db"], 10.0 * np.log10(expected_linear), places=6)
        self.assertAlmostEqual(result["mean_bin_linear"], expected_mean_bin, places=9)
        self.assertAlmostEqual(result["mean_bin_db"], 10.0 * np.log10(expected_mean_bin), places=6)

    def test_average_recent_noise_samples_applies_time_window(self):
        samples = [
            (1.00, 1.0),
            (1.20, 3.0),
            (1.55, 5.0),
            (1.80, 7.0),
        ]

        average = average_recent_noise_samples(samples, 0.5, now_s=1.80)

        self.assertAlmostEqual(average, (5.0 + 7.0) / 2.0, places=9)

    def test_auto_gain_table_widget_exposes_band_pair(self):
        widget = AutoGainTableWidget()
        widget.set_current_frequency(414_500_000.0)
        lna_state, if_gain = widget.get_active_pair_for_frequency(414_500_000.0)
        self.assertGreaterEqual(lna_state, 0)
        self.assertGreaterEqual(if_gain, 20)
        self.assertEqual(widget.selected_level_dbm, -60)
        self.assertGreaterEqual(lna_attenuation_db(414_500_000.0, lna_state), 0)
        widget.deleteLater()

    def test_default_auto_gain_profiles_match_reference_table(self):
        profiles = build_default_auto_gain_profiles()
        self.assertEqual(profiles[-100][0], (0, 40))
        self.assertEqual(profiles[-70][4], (0, 59))
        self.assertEqual(profiles[-70][6], (1, 50))
        self.assertEqual(profiles[-60][9], (3, 59))
        self.assertEqual(profiles[-20][10], (12, 59))
        self.assertEqual(profiles[0][4], (22, 59))
        self.assertEqual(profiles[20][10], (18, 59))


if __name__ == "__main__":
    unittest.main()
