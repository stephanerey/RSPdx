# src/gui/plots.py
import collections, math, time
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject
import pyqtgraph as pg
import numpy as np

pg.setConfigOptions(antialias=False)

class SpectrumPlotWidget(QObject):
    receiver_frequency_changed = pyqtSignal(float)
    receiver_bandwidth_changed = pyqtSignal(float)
    visible_span_changed = pyqtSignal(float, int)

    def __init__(self, layout, center_freq):
        super().__init__()
        if not isinstance(layout, pg.GraphicsLayoutWidget):
            raise ValueError("layout must be instance of pyqtgraph.GraphicsLayoutWidget")
        self.layout = layout
        self.center_freq = center_freq
        self.main_curve = True
        self.main_color = pg.mkColor(110, 235, 255)
        self.main_fill_brush = pg.mkBrush(20, 95, 120, 120)
        self.main_fill_level = -120.0
        self.persistence = False
        self.persistence_length = 5
        self.persistence_decay = "exponential"
        self.persistence_color = pg.mkColor("g")
        self.persistence_data = None
        self.persistence_curves = None
        self.peak_hold_max = False
        self.peak_hold_max_color = pg.mkColor("r")
        self.fft_hold_decay = True
        self.fft_hold_speed = 0.20  # dB par frame
        self._fft_hold_line = None
        self.peak_hold_min = False
        self.peak_hold_min_color = pg.mkColor("b")
        self.average = False
        self.average_color = pg.mkColor("c")
        self.baseline = False
        self.baseline_color = pg.mkColor("m")
        self.subtract_baseline = False
        # Affichage "crêtes" en mode subtract
        self.peaks_only = True  # n’afficher que les crêtes
        self.peaks_threshold_db = 3.0  # seuil au-dessus de la baseline (ex: ≥ +3 dB)
        self.subtracted_color = pg.mkColor('w')
        self._last_pen_mode_subtract = None
        self.create_plot()
        self.rx_overlays = {}  # name -> {"line": InfiniteLine, "region": LinearRegionItem}
        self._active_name = None  # nom du RX actif (celui dont les items sont déplaçables)

        self.subtract_baseline = False
        self.subtracted_color = pg.mkColor('w')  # white line for “crest”
        self.show_positive_peaks_only = True  # clip negatives after subtract
        self.peak_floor_db = -20.0  # keep a little floor so line doesn't vanish
        self._baseline_cache_key = None
        self._baseline_cache_y = None
        self._last_pen_mode_subtract = None
        self._guard = False  # <-- pour éviter les boucles de signaux
        self._last_xrange = None
        self._normal_yrange_set = False
        # Mode enveloppe désactivé par défaut pour garder une réponse burst rapide.
        self.envelope_mode = False
        self.envelope_decay_db = 20.0
        self._envelope_line = None
        self.max_display_bins = 8192
        self.fill_display_bins = 4096
        self._pending_visible_span = 0.0
        self._pending_plot_width = 0
        self._last_visible_span_emit = None
        self._visible_span_timer = QtCore.QTimer(self)
        self._visible_span_timer.setSingleShot(True)
        self._visible_span_timer.setInterval(120)
        self._visible_span_timer.timeout.connect(self._emit_visible_span)

    def create_plot(self):
        self.posLabel = self.layout.addLabel(row=0, col=0, justify="right")
        self.plot = self.layout.addPlot(row=1, col=0)
        self.plot.showGrid(x=True, y=True)
        self.plot.setLabel("left", "Power", units="dB")
        self.plot.setLabel("bottom", "Frequency", units="Hz")
        self.plot.setLimits(xMin=0)
        self.plot.setClipToView(True)
        # "peak" affiche des barres min/max. "subsample" donne un tracé plus proche SDR++.
        self.plot.setDownsampling(auto=True, mode='subsample')
        self.plot.showButtons()
        self.plot.getViewBox().sigXRangeChanged.connect(self._on_view_xrange_changed)

        self.create_baseline_curve()
        self.create_persistence_curves()
        self.create_average_curve()
        self.create_peak_hold_min_curve()
        self.create_peak_hold_max_curve()
        self.create_main_curve()

        # Crosshair
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen='cyan')
        self.hLine = pg.InfiniteLine(angle=0,  movable=False, pen='cyan')
        self.vLine.setZValue(1000); self.hLine.setZValue(1000)
        self.plot.addItem(self.vLine, ignoreBounds=True)
        self.plot.addItem(self.hLine, ignoreBounds=True)
        self.mouseProxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=30, slot=self.mouse_moved)

    def _on_view_xrange_changed(self, *_args):
        try:
            xr = self.plot.getViewBox().viewRange()[0]
            span = abs(float(xr[1]) - float(xr[0]))
            width_px = int(max(1, round(self.plot.getViewBox().sceneBoundingRect().width())))
        except Exception:
            return
        if not np.isfinite(span) or span <= 0.0:
            return
        self._pending_visible_span = span
        self._pending_plot_width = width_px
        self._visible_span_timer.start()

    def _emit_visible_span(self):
        span = float(self._pending_visible_span)
        width_px = int(max(1, self._pending_plot_width))
        if not np.isfinite(span) or span <= 0.0:
            return
        key = (round(span, 3), width_px)
        if self._last_visible_span_emit == key:
            return
        self._last_visible_span_emit = key
        self.visible_span_changed.emit(span, width_px)

    # --- synchro ligne/region
    def update_region_from_line(self):
        """(Actif uniquement) Déplacement de la ligne -> met à jour sa région + émet les signaux."""
        if getattr(self, "_guard", False) or self._active_name is None:
            return
        o = self.rx_overlays.get(self._active_name)
        if not o:
            return
        new_freq = o["line"].value()
        r0, r1 = o["region"].getRegion()
        bw = (r1 - r0)
        o["region"].setRegion([new_freq - bw / 2, new_freq + bw / 2])
        self.receiver_frequency_changed.emit(new_freq)

    def update_line_from_region(self):
        """(Actif uniquement) Déplacement de la région -> met à jour la ligne + émet les signaux."""
        if getattr(self, "_guard", False) or self._active_name is None:
            return
        o = self.rx_overlays.get(self._active_name)
        if not o:
            return
        r0, r1 = o["region"].getRegion()
        new_freq = 0.5 * (r0 + r1)
        new_bw = (r1 - r0)
        o["line"].setValue(new_freq)
        self.receiver_frequency_changed.emit(new_freq)
        self.receiver_bandwidth_changed.emit(new_bw)

    def set_receiver_selection(self, freq_hz: float, bw_hz: float):
        """Compat: met à jour l’overlay du RX actif (sans réémettre)."""
        if self._active_name is None:
            return
        self.update_rx_overlay(self._active_name, freq_hz, bw_hz)

    def ensure_rx_overlay(self, name: str, color, freq_hz: float, bw_hz: float, active: bool = False):
        """
        Crée si besoin (sinon met à jour) l’overlay d’un RX. Tous les RX sont visibles.
        Seul le RX actif est déplaçable/redimensionnable.
        """
        o = self.rx_overlays.get(name)
        qcol = pg.mkColor(color)

        if o is None:
            # --- create
            line = pg.InfiniteLine(pos=freq_hz, angle=90, movable=False, pen=pg.mkPen(qcol))
            line.setZValue(950)  # sous la région pour que les poignées de la région restent “cliquables”
            region = pg.LinearRegionItem(
                values=[freq_hz - bw_hz / 2, freq_hz + bw_hz / 2],
                orientation='vertical',
                brush=pg.mkBrush(qcol.red(), qcol.green(), qcol.blue(), 80),
                movable=False
            )
            # handles on top
            region.setZValue(960)

            # optionnel: un hover un peu plus opaque pour mieux voir les poignées
            try:
                region.setHoverBrush(pg.mkBrush(qcol.red(), qcol.green(), qcol.blue(), 120))
            except Exception:
                pass

            self.plot.addItem(region)
            self.plot.addItem(line)
            self.rx_overlays[name] = {"line": line, "region": region}
        else:
            # --- update pos/couleur
            self.update_rx_overlay(name, freq_hz, bw_hz)
            self.set_rx_color(name, qcol)

        # activer ce RX ?
        if active:
            self.set_active_rx(name)

    def update_rx_overlay(self, name: str, freq_hz: float = None, bw_hz: float = None):
        """Met à jour position (ligne + région) du RX 'name' (sans signaux)."""
        o = self.rx_overlays.get(name)
        if not o:
            return
        try:
            self._guard = True
            if freq_hz is not None:
                o["line"].setValue(freq_hz)
            if bw_hz is not None:
                c = o["line"].value() if freq_hz is None else freq_hz
                o["region"].setRegion([c - bw_hz / 2, c + bw_hz / 2])
            # Toujours visibles (tous les RX)
            o["line"].setVisible(True)
            o["region"].setVisible(True)
        finally:
            self._guard = False

    def set_rx_color(self, name: str, color):
        """Set overlay color (line + region) for RX 'name'."""
        o = self.rx_overlays.get(name)
        if not o:
            return
        qcol = pg.mkColor(color)
        o["line"].setPen(pg.mkPen(qcol))
        o["region"].setBrush(pg.mkBrush(qcol.red(), qcol.green(), qcol.blue(), 80))

    def set_active_rx(self, name: str):
        """
        Définit le RX actif :
          - sa ligne + sa région deviennent déplaçables ;
          - les poignées de la région sont au-dessus de la ligne (Z) pour être saisissables ;
          - les autres RX restent visibles mais figés.
        """
        # désactiver l'ancien
        if self._active_name is not None and self._active_name in self.rx_overlays:
            prev = self.rx_overlays[self._active_name]
            for sig, slot in [(prev["line"].sigPositionChanged, self.update_region_from_line),
                              (prev["region"].sigRegionChanged, self.update_line_from_region)]:
                try:
                    sig.disconnect(slot)
                except Exception:
                    pass
            prev["line"].setMovable(False)
            prev["region"].setMovable(False)
            p = prev["line"].pen;
            p.setWidth(1);
            prev["line"].setPen(p)
            prev["region"].setZValue(960)  # on laisse au-dessus pour visibilité des poignées si jamais
            prev["line"].setZValue(950)

        # activer le nouveau
        self._active_name = name
        cur = self.rx_overlays.get(name)
        if not cur:
            return

        cur["line"].setMovable(True)
        cur["region"].setMovable(True)

        # épaissir la ligne de l'actif
        p = cur["line"].pen;
        p.setWidth(2);
        cur["line"].setPen(p)

        # s'assurer que la région est au-dessus pour pouvoir attraper les bords et redimensionner
        cur["region"].setZValue(960)
        cur["line"].setZValue(950)

        # connecter les signaux UNIQUEMENT pour l'actif (déplacement + redimensionnement)
        cur["line"].sigPositionChanged.connect(self.update_region_from_line)
        cur["region"].sigRegionChanged.connect(self.update_line_from_region)

    def set_selection_color(self, qcolor):
        """Compat: colore l’overlay du RX actif."""
        if self._active_name is None:
            return
        self.set_rx_color(self._active_name, qcolor)

    def update_selected_freq_line(self, new_center_freq, bw=25e3):
        # Multi-RX: on ne force plus un overlay unique ici.
        # On garde juste la valeur locale pour information.
        self.center_freq = new_center_freq

    def update_center_frequency(self, new_center_freq):
        # Multi-RX: idem, ne pas toucher aux overlays ici.
        self.center_freq = new_center_freq

    def snapshot_baseline_from(self, data_storage, window_pts: int = 151):
        if data_storage.x is None or data_storage.y is None:
            return
        y = np.asarray(data_storage.y, dtype=np.float32)
        k = max(1, int(window_pts))
        if k % 2 == 0: k += 1
        if k > 1:
            kernel = np.ones(k, dtype=np.float32) / k
            y_smooth = np.convolve(y, kernel, mode="same")
        else:
            y_smooth = y
        data_storage.baseline_x = np.asarray(data_storage.x, dtype=np.float64).copy()
        data_storage.baseline = np.asarray(y_smooth, dtype=np.float32).copy()

    def create_main_curve(self):
        self.curve_fill = self.plot.plot(pen=None)
        self.curve_fill.setFillLevel(self.main_fill_level)
        self.curve_fill.setBrush(self.main_fill_brush)
        self.curve_fill.setZValue(880)
        self.curve = self.plot.plot(pen=self.main_color)
        self.curve.setZValue(900)

    def create_peak_hold_max_curve(self):
        self.curve_peak_hold_max = self.plot.plot(pen=self.peak_hold_max_color)
        self.curve_peak_hold_max.setZValue(800)

    def create_peak_hold_min_curve(self):
        self.curve_peak_hold_min = self.plot.plot(pen=self.peak_hold_min_color)
        self.curve_peak_hold_min.setZValue(800)

    def create_average_curve(self):
        self.curve_average = self.plot.plot(pen=self.average_color)
        self.curve_average.setZValue(700)

    def create_baseline_curve(self):
        self.curve_baseline = self.plot.plot(pen=self.baseline_color)
        self.curve_baseline.setZValue(500)

    def create_persistence_curves(self):
        z_index_base = 600
        decay = self.get_decay()
        self.persistence_curves = []
        for i in range(self.persistence_length):
            alpha = 255 * decay(i + 1, self.persistence_length + 1)
            color = self.persistence_color
            curve = self.plot.plot(pen=(color.red(), color.green(), color.blue(), alpha))
            curve.setZValue(z_index_base - i)
            self.persistence_curves.append(curve)

    def _baseline_for_x(self, x: np.ndarray, bx: np.ndarray, by: np.ndarray) -> np.ndarray:
        """
        Retourne baseline rééchantillonnée sur x.
        - Fast-path si x == bx (même grille) : renvoie by tel quel.
        - Sinon: interpolation *mise en cache* pour la même grille x et même baseline.
        """
        x = np.asarray(x, dtype=np.float64)
        bx = np.asarray(bx, dtype=np.float64)
        by = np.asarray(by, dtype=np.float64)

        # 1) même grille -> zéro coût
        if len(x) == len(bx) and np.allclose(x, bx, rtol=0.0, atol=1e-9):
            return by.astype(np.float32, copy=False)

        # 2) cache (clé: (len, x0, x1, id(bx), id(by)))
        key = (int(x.size), float(x[0]), float(x[-1]), id(bx), id(by))
        if key == self._baseline_cache_key and self._baseline_cache_y is not None:
            return self._baseline_cache_y

        # 3) interp une fois puis cache
        base = np.interp(x, bx, by, left=float(by[0]), right=float(by[-1])).astype(np.float32)
        self._baseline_cache_key = key
        self._baseline_cache_y = base
        return base

    def _maybe_update_pen(self):
        """Ne change la couleur/épaisseur qu'en cas de changement de mode, pour éviter du boulot inutile."""
        mode = bool(self.subtract_baseline)
        if mode != self._last_pen_mode_subtract:
            if mode:
                self.curve.setPen(pg.mkPen(self.subtracted_color, width=2))
                self.curve_fill.clear()
            else:
                self.curve.setPen(self.main_color)
                self.curve_fill.setFillLevel(self.main_fill_level)
                self.curve_fill.setBrush(self.main_fill_brush)
            self._last_pen_mode_subtract = mode

    def _current_y_with_options(self, data_storage):
        y = np.asarray(data_storage.y, dtype=np.float32)

        # Lissage côté DataStorage si dispo
        if getattr(data_storage, "smooth", False):
            try:
                y = data_storage.smooth_data(y)
            except Exception:
                pass

        # Soustraction baseline (rapide si même grille)
        if (self.subtract_baseline and
                getattr(data_storage, "baseline", None) is not None and
                getattr(data_storage, "baseline_x", None) is not None and
                len(data_storage.baseline) >= 2):

            x = np.asarray(data_storage.x, dtype=np.float64)
            bx = np.asarray(data_storage.baseline_x, dtype=np.float64)
            by = np.asarray(data_storage.baseline, dtype=np.float64)

            if len(x) == len(bx) and np.allclose(x, bx, rtol=0.0, atol=1e-9):
                base = by.astype(np.float32, copy=False)
            else:
                base = np.interp(x, bx, by, left=float(by[0]), right=float(by[-1])).astype(np.float32)

            y = y - base

            # N’afficher QUE les crêtes > seuil (masque le reste via NaN -> lignes fines)
            if self.peaks_only:
                y = np.where(y >= self.peaks_threshold_db, y, np.nan).astype(np.float32)

        # Nettoyage des non-finis (on garde NaN pour “casser” la ligne là où il n’y a rien)
        # → pyqtgraph ignore les NaN, parfait pour l'effet pics fins
        return y

    def set_colors(self):
        self.curve.setPen(self.main_color)
        if not self.subtract_baseline:
            self.curve_fill.setFillLevel(self.main_fill_level)
            self.curve_fill.setBrush(self.main_fill_brush)
        self.curve_peak_hold_max.setPen(self.peak_hold_max_color)
        self.curve_peak_hold_min.setPen(self.peak_hold_min_color)
        self.curve_average.setPen(self.average_color)
        self.curve_baseline.setPen(self.baseline_color)
        decay = self.get_decay()
        for i, curve in enumerate(self.persistence_curves):
            alpha = 255 * decay(i + 1, self.persistence_length + 1)
            color = self.persistence_color
            curve.setPen((color.red(), color.green(), color.blue(), alpha))

    def decay_linear(self, x, length):        return (-x / length) + 1
    def decay_exponential(self, x, length, const=1/3): return math.e**(-x / (length * const))
    def get_decay(self): return self.decay_exponential if self.persistence_decay == 'exponential' else self.decay_linear

    def update_plot(self, data_storage, force=False):
        if data_storage.x is None:
            return

        y_plot = self._current_y_with_options(data_storage)
        if self.envelope_mode and not self.subtract_baseline:
            y_now = np.asarray(y_plot, dtype=np.float32)
            if self._envelope_line is None or self._envelope_line.shape != y_now.shape:
                self._envelope_line = y_now.copy()
            else:
                self._envelope_line = np.maximum(y_now, self._envelope_line - float(self.envelope_decay_db))
            y_plot = self._envelope_line
        peak_bins = self._display_peak_bins()
        x_plot, y_peak = self._decimate_line_for_display(data_storage.x, y_plot, mode="peak", max_bins=peak_bins)

        # Axe Y : si subtract -> plage compacte autour des pics visibles
        if self.subtract_baseline:
            # nanmax ignore les NaN; si tout est NaN, on met une petite plage par défaut
            try:
                y_max = float(np.nanmax(y_peak))
                y_min = 0.0 if self.peaks_only else float(np.nanmin(y_peak))
            except ValueError:
                y_min, y_max = 0.0, 6.0  # pas de pics visibles
            self.plot.setYRange(y_min - 1.0, y_max + 3.0)
            self._normal_yrange_set = False
        else:
            if not self._normal_yrange_set:
                self.plot.setYRange(-60, 40)
                self._normal_yrange_set = True

        x0 = float(data_storage.x[0])
        x1 = float(data_storage.x[-1])
        xr = (x0, x1)
        if self._last_xrange != xr:
            self.plot.setXRange(x0, x1)
            self._last_xrange = xr

        if self.main_curve or force:
            # ne change le pen que si nécessaire
            if self.subtract_baseline != self._last_pen_mode_subtract:
                if self.subtract_baseline:
                    self.curve.setPen(pg.mkPen(self.subtracted_color, width=2))
                    self.curve_fill.clear()
                else:
                    self.curve.setPen(self.main_color)
                    self.curve_fill.setFillLevel(self.main_fill_level)
                    self.curve_fill.setBrush(self.main_fill_brush)
                self._last_pen_mode_subtract = self.subtract_baseline

            # IMPORTANT: connect='finite' pour que pyqtgraph ignore les NaN proprement
            if self.subtract_baseline:
                self.curve_fill.clear()
            else:
                self.curve_fill.setData(x_plot, y_peak, connect='finite')
            self.curve.setData(x_plot, y_peak, connect='finite')
            self.curve.setVisible(True)
            self.curve_fill.setVisible(not self.subtract_baseline and self.main_curve)

    def _decimate_line_for_display(self, x, y, mode="peak", max_bins=None):
        x = np.asarray(x)
        y = np.asarray(y)
        n = int(y.size)
        max_bins = int(max(512, self.max_display_bins if max_bins is None else max_bins))
        if n <= max_bins:
            return x, y
        step = int(np.ceil(n / float(max_bins)))
        m = int(np.ceil(n / float(step)))
        pad = m * step - n
        if pad > 0:
            x_pad = np.pad(x, (0, pad), mode='edge')
            y_pad = np.pad(y, (0, pad), mode='edge')
        else:
            x_pad = x
            y_pad = y
        x_r = x_pad.reshape(m, step)
        y_r = y_pad.reshape(m, step)
        with np.errstate(all='ignore'):
            if mode == "median":
                y_d = np.nanmedian(y_r, axis=1)
            elif mode == "mean":
                y_d = np.nanmean(y_r, axis=1)
            else:
                y_d = np.nanmax(y_r, axis=1)
        y_d = np.where(np.isfinite(y_d), y_d, np.nan)
        x_d = x_r[:, step // 2]
        return x_d, y_d

    def _display_peak_bins(self):
        try:
            vb = self.plot.getViewBox()
            width_px = int(max(256, round(vb.sceneBoundingRect().width())))
        except Exception:
            width_px = 1024
        return int(min(self.max_display_bins, max(512, width_px)))

    def update_peak_hold_max(self, data_storage, force=False):
        if data_storage.x is None: return
        if self.peak_hold_max or force:
            y_raw = getattr(data_storage, "y", None)
            if y_raw is None:
                if force:
                    self.curve_peak_hold_max.clear()
                return
            y = np.asarray(y_raw, dtype=np.float32)
            if y.size == 0:
                if force:
                    self.curve_peak_hold_max.clear()
                return
            if self._fft_hold_line is None or self._fft_hold_line.shape != y.shape:
                self._fft_hold_line = y.copy()
            else:
                if self.fft_hold_decay:
                    self._fft_hold_line = np.maximum(y, self._fft_hold_line - float(self.fft_hold_speed))
                else:
                    self._fft_hold_line = np.maximum(self._fft_hold_line, y)
            self.curve_peak_hold_max.setData(data_storage.x, self._fft_hold_line)
            if force:
                self.curve_peak_hold_max.setVisible(self.peak_hold_max)

    def update_peak_hold_min(self, data_storage, force=False):
        if data_storage.x is None: return
        if self.peak_hold_min or force:
            y = getattr(data_storage, "peak_hold_min", None)
            if y is None:
                if force:
                    self.curve_peak_hold_min.clear()
                return
            self.curve_peak_hold_min.setData(data_storage.x, data_storage.peak_hold_min)
            if force: self.curve_peak_hold_min.setVisible(self.peak_hold_min)

    def update_average(self, data_storage, force=False):
        if data_storage.x is None: return
        if self.average or force:
            y = getattr(data_storage, "average", None)
            if y is None:
                if force:
                    self.curve_average.clear()
                return
            self.curve_average.setData(data_storage.x, data_storage.average)
            if force: self.curve_average.setVisible(self.average)

    def update_baseline(self, data_storage, force=False):
        if data_storage.baseline_x is None or data_storage.baseline is None:
            self.curve_baseline.clear(); return
        if self.baseline or force:
            self.curve_baseline.setData(data_storage.baseline_x, data_storage.baseline)
            if force: self.curve_baseline.setVisible(self.baseline)

    def update_persistence(self, data_storage, force=False):
        if data_storage.x is None: return
        if self.persistence or force:
            if self.persistence_data is None:
                self.persistence_data = collections.deque(maxlen=self.persistence_length)
            else:
                for i, y in enumerate(self.persistence_data):
                    curve = self.persistence_curves[i]
                    curve.setData(data_storage.x, y)
                    if force: curve.setVisible(self.persistence)
            self.persistence_data.appendleft(data_storage.y)

    def recalculate_plot(self, data_storage):
        if data_storage.x is None: return
        QtCore.QTimer.singleShot(0, lambda: self.update_plot(data_storage, force=True))
        QtCore.QTimer.singleShot(0, lambda: self.update_average(data_storage, force=True))
        QtCore.QTimer.singleShot(0, lambda: self.update_baseline(data_storage, force=True))
        QtCore.QTimer.singleShot(0, lambda: self.update_peak_hold_max(data_storage, force=True))
        QtCore.QTimer.singleShot(0, lambda: self.update_peak_hold_min(data_storage, force=True))

    def recalculate_persistence(self, data_storage):
        if data_storage.x is None: return
        self.clear_persistence()
        self.persistence_data = collections.deque(maxlen=self.persistence_length)
        for i in range(min(self.persistence_length, data_storage.history.history_size - 1)):
            data = data_storage.history[-i - 2]
            if data_storage.smooth:
                data = data_storage.smooth_data(data)
            self.persistence_data.append(data)
        QtCore.QTimer.singleShot(0, lambda: self.update_persistence(data_storage, force=True))

    def mouse_moved(self, evt):
        pos = evt[0]
        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = self.plot.vb.mapSceneToView(pos)
            self.posLabel.setText(
                "<span style='font-size: 12pt'>f={:0.3f} MHz, P={:0.3f} dB</span>".format(
                    mousePoint.x() / 1e6, mousePoint.y()))
            self.vLine.setPos(mousePoint.x()); self.hLine.setPos(mousePoint.y())

    # clears
    def clear_plot(self):
        self._envelope_line = None
        self._last_visible_span_emit = None
        self.curve_fill.clear()
        self.curve.clear()
    def clear_peak_hold_max(self):
        self._fft_hold_line = None
        self.curve_peak_hold_max.clear()
    def clear_peak_hold_min(self): self.curve_peak_hold_min.clear()
    def clear_average(self): self.curve_average.clear()
    def clear_baseline(self): self.curve_baseline.clear()
    def clear_persistence(self):
        self.persistence_data = None
        for curve in self.persistence_curves:
            curve.clear(); self.plot.removeItem(curve)
        self.create_persistence_curves()

class WaterfallPlotWidget:
    def __init__(self, layout, histogram_layout=None):
        import pyqtgraph as pg
        if not isinstance(layout, pg.GraphicsLayoutWidget):
            raise ValueError("layout must be instance of pyqtgraph.GraphicsLayoutWidget")
        if histogram_layout and not isinstance(histogram_layout, pg.GraphicsLayoutWidget):
            raise ValueError("histogram_layout must be instance of pyqtgraph.GraphicsLayoutWidget")
        self.layout = layout
        self.histogram_layout = histogram_layout
        self.history_size = 100
        self.counter = 0
        self.auto_levels = False
        self.wf_min_db = -120.0
        self.wf_max_db = -20.0
        self._levels_alpha = 0.10
        self._last_draw_t = 0.0
        self._draw_min_interval_s = 1.0 / 20.0
        self.max_bins = 32768
        self._last_transform_key = None
        self.create_plot()

    def create_plot(self):
        self.plot = self.layout.addPlot()
        self.plot.setLabel("bottom", "Frequency", units="Hz")
        self.plot.setLabel("left", "Time")
        self.plot.setYRange(-self.history_size, 0)
        self.plot.setLimits(xMin=0, yMax=0)
        self.plot.showButtons()

        if self.histogram_layout:
            self.histogram = pg.HistogramLUTItem()
            self.histogram_layout.addItem(self.histogram)
            self.histogram.gradient.loadPreset("flame")
        self.waterfallImg = None

    def _update_levels(self, line_db: np.ndarray):
        return

    def update_plot(self, data_storage):
        import pyqtgraph as pg
        if data_storage is None:
            return
        hist_src = getattr(data_storage, "waterfall_history", None)
        x_src = getattr(data_storage, "x_wf", None)
        if hist_src is None:
            hist_src = data_storage.history
            x_src = data_storage.x
        if hist_src is None or x_src is None:
            return
        now_t = time.monotonic()
        if now_t - self._last_draw_t < self._draw_min_interval_s:
            return
        hist = hist_src.get_recent(self.history_size)
        if hist is None or len(hist) == 0:
            return

        self.counter = int(min(self.history_size, hist.shape[0]))
        if self.waterfallImg is None:
            self.waterfallImg = pg.ImageItem()
            self.plot.clear()
            self.plot.addItem(self.waterfallImg)
            if self.histogram_layout:
                self.histogram.setImageItem(self.waterfallImg)

        view = np.asarray(hist[-self.counter:], dtype=np.float32)
        if view.shape[1] > int(self.max_bins):
            stride = int(np.ceil(view.shape[1] / float(self.max_bins)))
            view = view[:, ::stride]
            x_use = np.asarray(x_src, dtype=np.float64)[::stride]
        else:
            x_use = np.asarray(x_src, dtype=np.float64)
        lo = float(self.wf_min_db)
        hi = float(self.wf_max_db)
        rng = max(1e-3, hi - lo)
        z = np.clip((view - lo) / rng, 0.0, 1.0).astype(np.float32, copy=False)

        x0 = float(x_use[0])
        x1 = float(x_use[-1])
        bins = int(max(1, view.shape[1] - 1))
        tkey = (x0, x1, bins)
        if self._last_transform_key != tkey:
            self.waterfallImg.setTransform(pg.QtGui.QTransform().scale((x1 - x0) / bins, 1))
            self._last_transform_key = tkey
        self.waterfallImg.setImage(z.T, autoLevels=False, autoRange=False, levels=(0.0, 1.0))
        self.waterfallImg.setPos(x0, -self.counter if self.counter < self.history_size else -self.history_size)
        self._last_draw_t = now_t

    def clear_plot(self):
        self.counter = 0
        self.waterfallImg = None
        self._last_transform_key = None

    def recalculate_plot(self, data_storage):
        if data_storage is None or data_storage.x is None:
            return
        self.update_plot(data_storage)

class ConstellationPlotWidget:
    def __init__(self, layout):
        import pyqtgraph as pg
        if not isinstance(layout, pg.GraphicsLayoutWidget):
            raise ValueError("layout must be instance of pyqtgraph.GraphicsLayoutWidget")
        self.layout = layout
        self.create_plot()

    def create_plot(self):
        import pyqtgraph as pg
        self.plot = self.layout.addPlot(row=0, col=0, title="Constellation Diagram")
        self.plot.setLabel("left", "Quadrature Amplitude")
        self.plot.setLabel("bottom", "In-phase Amplitude")
        self.plot.setXRange(-2, 2); self.plot.setYRange(-2, 2)
        self.plot.showGrid(x=True, y=True)
        self.plot.setAspectLocked(True)
        self.scatter = pg.ScatterPlotItem(size=2, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 0, 120))
        self.plot.addItem(self.scatter)

    def update_plot(self, iq_data):
        if iq_data is None or len(iq_data) == 0:
            return
        iq_data = np.asarray(iq_data, dtype=np.complex64)
        if np.isnan(iq_data).any():
            return

        # Limiter le nombre de points affichés sans masquer les changements de forme.
        max_points = 6000
        if iq_data.size > max_points:
            stride = int(np.ceil(iq_data.size / max_points))
            iq_data = iq_data[::stride]

        # Normalisation RMS pour garder une constellation lisible (échelle stable).
        rms = float(np.sqrt(np.mean(np.abs(iq_data) ** 2))) if iq_data.size else 0.0
        if rms > 1e-9:
            iq_data = iq_data / rms

        i_data = iq_data.real
        q_data = iq_data.imag
        mask = ~np.isnan(i_data) & ~np.isnan(q_data)
        if not np.any(mask): return
        self.scatter.setData(i_data[mask], q_data[mask])
