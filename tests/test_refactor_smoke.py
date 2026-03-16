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
from src.gui.log_viewer_ui import LogViewerWidget
from src.gui.receiver_tab import ReceiverTab
from src.gui.threads_ui import ThreadsWidget
from src.threading_utils.thread_manager import ManagedTaskStatus, ThreadManager
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
        widget.deleteLater()


if __name__ == "__main__":
    unittest.main()
