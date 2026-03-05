import collections, math

from PyQt5 import QtCore, QtGui
import pyqtgraph as pg
import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject

# Basic PyQtGraph settings
pg.setConfigOptions(antialias=True)


class SpectrumPlotWidget(QObject):
    receiver_frequency_changed = pyqtSignal(float)
    receiver_bandwidth_changed = pyqtSignal(float)
    """Main spectrum plot"""
    def __init__(self, layout, center_freq):
        super().__init__()
        if not isinstance(layout, pg.GraphicsLayoutWidget):
            raise ValueError("layout must be instance of pyqtgraph.GraphicsLayoutWidget")

        self.layout = layout
        self.center_freq = center_freq
        self.main_curve = True
        self.main_color = pg.mkColor("y")
        self.persistence = False
        self.persistence_length = 5
        self.persistence_decay = "exponential"
        self.persistence_color = pg.mkColor("g")
        self.persistence_data = None
        self.persistence_curves = None
        self.peak_hold_max = False
        self.peak_hold_max_color = pg.mkColor("r")
        self.peak_hold_min = False
        self.peak_hold_min_color = pg.mkColor("b")
        self.average = False
        self.average_color = pg.mkColor("c")
        self.baseline = False
        self.baseline_color = pg.mkColor("m")

        self.create_plot()

    def create_plot(self):
        """Create main spectrum plot"""
        self.posLabel = self.layout.addLabel(row=0, col=0, justify="right")
        self.plot = self.layout.addPlot(row=1, col=0)
        self.plot.showGrid(x=True, y=True)
        self.plot.setLabel("left", "Power", units="dB")
        self.plot.setLabel("bottom", "Frequency", units="Hz")
        self.plot.setLimits(xMin=0)
        self.plot.showButtons()

        #self.plot.setDownsampling(mode="peak")
        # self.plot.setClipToView(True)

        self.create_baseline_curve()
        self.create_persistence_curves()
        self.create_average_curve()
        self.create_peak_hold_min_curve()
        self.create_peak_hold_max_curve()
        self.create_main_curve()

        # Create crosshair
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen='cyan')
        self.vLine.setZValue(1000)
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen='cyan')
        self.vLine.setZValue(1000)
        self.plot.addItem(self.vLine, ignoreBounds=True)
        self.plot.addItem(self.hLine, ignoreBounds=True)
        self.mouseProxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=30, slot=self.mouse_moved)

        self.selected_freq = pg.InfiniteLine(pos=self.center_freq, angle=90, movable=True, pen='r')
        self.plot.addItem(self.selected_freq)
        self.bandwidth_region = pg.LinearRegionItem(
            values=[self.center_freq - 12.5e3, self.center_freq + 12.5e3],
            brush=pg.mkBrush(255, 0, 0, 80),
            movable=True  # ✅ Permet de déplacer la zone avec la souris
        )
        self.plot.addItem(self.bandwidth_region)
        self.selected_freq.sigPositionChanged.connect(self.update_region_from_line)
        self.bandwidth_region.sigRegionChanged.connect(self.update_line_from_region)

    def update_selected_frequency(self):
        """Callback appelée lorsque l'utilisateur bouge la ligne de fréquence"""
        new_freq = self.selected_freq.value()
        bw = 25e3  # Exemple : 25 kHz de bande passante
        self.receiver_frequency_changed.emit(new_freq)
        self.bandwidth_region.setRegion([new_freq - bw / 2, new_freq + bw / 2])

    def update_selected_freq_line(self, new_center_freq, bw=25e3):
        """Met à jour la position de la ligne de fréquence sélectionnée"""
        self.center_freq = new_center_freq  # Mettre à jour la fréquence centrale stockée
        self.selected_freq.setValue(self.center_freq)  # Déplacer la ligne rouge
        # QtWidgets.QApplication.processEvents()  # Rafraîchir l'affichage

    def update_region_from_line(self):
        """Déplace la bande passante si la ligne rouge bouge"""
        new_freq = self.selected_freq.value()
        bw = self.bandwidth_region.getRegion()[1] - self.bandwidth_region.getRegion()[0]  # Largeur actuelle
        self.bandwidth_region.setRegion([new_freq - bw / 2, new_freq + bw / 2])
        self.receiver_frequency_changed.emit(new_freq)  # 🔥 Signale le changement

    def update_line_from_region(self):
        """Déplace la ligne rouge et met à jour la bande passante si la région est modifiée."""
        region = self.bandwidth_region.getRegion()  # 📍 Récupère les nouvelles limites de la bande
        new_freq = sum(region) / 2  # 🔄 Calcule le centre
        new_bandwidth = region[1] - region[0]  # 🔄 Calcule la nouvelle largeur de bande

        self.selected_freq.setValue(new_freq)  # 🔄 Déplace la ligne rouge
        self.bandwidth = new_bandwidth  # 🆕 Met à jour la bande passante pour le filtre

        self.receiver_frequency_changed.emit(new_freq)  # 🔥 Informe le SDR du changement de fréquence
        self.receiver_bandwidth_changed.emit(new_bandwidth)  # 🔥 Informe du changement de bande passante

    def update_center_frequency(self, new_center_freq):
        """Met à jour la fréquence centrale et repositionne la ligne de fréquence sélectionnée"""
        self.center_freq = new_center_freq  # Met à jour la fréquence centrale du spectre
        self.selected_freq.setValue(self.center_freq)  # Déplace la ligne rouge
        self.bandwidth_region.setRegion([new_center_freq - bw / 2, new_center_freq + bw / 2])

    def create_main_curve(self):
        """Create main spectrum curve"""
        self.curve = self.plot.plot(pen=self.main_color)
        self.curve.setZValue(900)

    def create_peak_hold_max_curve(self):
        """Create max. peak hold curve"""
        self.curve_peak_hold_max = self.plot.plot(pen=self.peak_hold_max_color)
        self.curve_peak_hold_max.setZValue(800)

    def create_peak_hold_min_curve(self):
        """Create min. peak hold curve"""
        self.curve_peak_hold_min = self.plot.plot(pen=self.peak_hold_min_color)
        self.curve_peak_hold_min.setZValue(800)

    def create_average_curve(self):
        """Create average curve"""
        self.curve_average = self.plot.plot(pen=self.average_color)
        self.curve_average.setZValue(700)

    def create_baseline_curve(self):
        """Create baseline curve"""
        self.curve_baseline = self.plot.plot(pen=self.baseline_color)
        self.curve_baseline.setZValue(500)

    def create_persistence_curves(self):
        """Create spectrum persistence curves"""
        z_index_base = 600
        decay = self.get_decay()
        self.persistence_curves = []
        for i in range(self.persistence_length):
            alpha = 255 * decay(i + 1, self.persistence_length + 1)
            color = self.persistence_color
            curve = self.plot.plot(pen=(color.red(), color.green(), color.blue(), alpha))
            curve.setZValue(z_index_base - i)
            self.persistence_curves.append(curve)

    def set_colors(self):
        """Set colors of all curves"""
        self.curve.setPen(self.main_color)
        self.curve_peak_hold_max.setPen(self.peak_hold_max_color)
        self.curve_peak_hold_min.setPen(self.peak_hold_min_color)
        self.curve_average.setPen(self.average_color)
        self.curve_baseline.setPen(self.baseline_color)

        decay = self.get_decay()
        for i, curve in enumerate(self.persistence_curves):
            alpha = 255 * decay(i + 1, self.persistence_length + 1)
            color = self.persistence_color
            curve.setPen((color.red(), color.green(), color.blue(), alpha))

    def decay_linear(self, x, length):
        """Get alpha value for persistence curve (linear decay)"""
        return (-x / length) + 1

    def decay_exponential(self, x, length, const=1 / 3):
        """Get alpha value for persistence curve (exponential decay)"""
        return math.e**(-x / (length * const))

    def get_decay(self):
        """Get decay function"""
        if self.persistence_decay == 'exponential':
            return self.decay_exponential
        else:
            return self.decay_linear

    def update_plot(self, data_storage, force=False):
        """Update main spectrum curve"""
        if data_storage.x is None:
            return
        self.plot.setYRange(-60, 40)

        self.plot.setXRange(data_storage.x[0], data_storage.x[-1])

        if self.main_curve or force:
            self.curve.setData(data_storage.x, data_storage.y)
            if force:
                self.curve.setVisible(self.main_curve)

        #self.update_selected_freq_line(self.center_freq)

    def update_peak_hold_max(self, data_storage, force=False):
        """Update max. peak hold curve"""
        if data_storage.x is None:
            return

        if self.peak_hold_max or force:
            self.curve_peak_hold_max.setData(data_storage.x, data_storage.peak_hold_max)
            if force:
                self.curve_peak_hold_max.setVisible(self.peak_hold_max)

    def update_peak_hold_min(self, data_storage, force=False):
        """Update min. peak hold curve"""
        if data_storage.x is None:
            return

        if self.peak_hold_min or force:
            self.curve_peak_hold_min.setData(data_storage.x, data_storage.peak_hold_min)
            if force:
                self.curve_peak_hold_min.setVisible(self.peak_hold_min)

    def update_average(self, data_storage, force=False):
        """Update average curve"""
        if data_storage.x is None:
            return

        if self.average or force:
            self.curve_average.setData(data_storage.x, data_storage.average)
            if force:
                self.curve_average.setVisible(self.average)

    def update_baseline(self, data_storage, force=False):
        """Update baseline curve"""
        if data_storage.baseline_x is None or data_storage.baseline is None:
            self.curve_baseline.clear()
            return

        if self.baseline or force:
            self.curve_baseline.setData(data_storage.baseline_x, data_storage.baseline)
            if force:
                self.curve_baseline.setVisible(self.baseline)

    def update_persistence(self, data_storage, force=False):
        """Update persistence curves"""
        if data_storage.x is None:
            return

        if self.persistence or force:
            if self.persistence_data is None:
                self.persistence_data = collections.deque(maxlen=self.persistence_length)
            else:
                for i, y in enumerate(self.persistence_data):
                    curve = self.persistence_curves[i]
                    curve.setData(data_storage.x, y)
                    if force:
                        curve.setVisible(self.persistence)
            self.persistence_data.appendleft(data_storage.y)

    def recalculate_plot(self, data_storage):
        """Recalculate plot from history"""
        if data_storage.x is None:
            return

        QtCore.QTimer.singleShot(0, lambda: self.update_plot(data_storage, force=True))
        QtCore.QTimer.singleShot(0, lambda: self.update_average(data_storage, force=True))
        QtCore.QTimer.singleShot(0, lambda: self.update_baseline(data_storage, force=True))
        QtCore.QTimer.singleShot(0, lambda: self.update_peak_hold_max(data_storage, force=True))
        QtCore.QTimer.singleShot(0, lambda: self.update_peak_hold_min(data_storage, force=True))

    def recalculate_persistence(self, data_storage):
        """Recalculate persistence data and update persistence curves"""
        if data_storage.x is None:
            return

        self.clear_persistence()
        self.persistence_data = collections.deque(maxlen=self.persistence_length)
        for i in range(min(self.persistence_length, data_storage.history.history_size - 1)):
            data = data_storage.history[-i - 2]
            if data_storage.smooth:
                data = data_storage.smooth_data(data)
            self.persistence_data.append(data)
        QtCore.QTimer.singleShot(0, lambda: self.update_persistence(data_storage, force=True))

    def mouse_moved(self, evt):
        """Update crosshair when mouse is moved"""
        pos = evt[0]
        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = self.plot.vb.mapSceneToView(pos)
            self.posLabel.setText(
                "<span style='font-size: 12pt'>f={:0.3f} MHz, P={:0.3f} dB</span>".format(
                    mousePoint.x() / 1e6,
                    mousePoint.y()
                )
            )
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def clear_plot(self):
        """Clear main spectrum curve"""
        self.curve.clear()

    def clear_peak_hold_max(self):
        """Clear max. peak hold curve"""
        self.curve_peak_hold_max.clear()

    def clear_peak_hold_min(self):
        """Clear min. peak hold curve"""
        self.curve_peak_hold_min.clear()

    def clear_average(self):
        """Clear average curve"""
        self.curve_average.clear()

    def clear_baseline(self):
        """Clear baseline curve"""
        self.curve_baseline.clear()

    def clear_persistence(self):
        """Clear spectrum persistence curves"""
        self.persistence_data = None
        for curve in self.persistence_curves:
            curve.clear()
            self.plot.removeItem(curve)
        self.create_persistence_curves()


class WaterfallPlotWidget:
    """Waterfall plot"""
    def __init__(self, layout, histogram_layout=None):
        if not isinstance(layout, pg.GraphicsLayoutWidget):
            raise ValueError("layout must be instance of pyqtgraph.GraphicsLayoutWidget")

        if histogram_layout and not isinstance(histogram_layout, pg.GraphicsLayoutWidget):
            raise ValueError("histogram_layout must be instance of pyqtgraph.GraphicsLayoutWidget")

        self.layout = layout
        self.histogram_layout = histogram_layout

        self.history_size = 100
        self.counter = 0

        self.create_plot()

    def create_plot(self):
        """Create waterfall plot"""
        self.plot = self.layout.addPlot()
        self.plot.setLabel("bottom", "Frequency", units="Hz")
        self.plot.setLabel("left", "Time")

        self.plot.setYRange(-self.history_size, 0)
        self.plot.setLimits(xMin=0, yMax=0)
        self.plot.showButtons()
        #self.plot.setAspectLocked(True)

        #self.plot.setDownsampling(mode="peak")
        #self.plot.setClipToView(True)

        # Setup histogram widget (for controlling waterfall plot levels and gradients)
        if self.histogram_layout:
            self.histogram = pg.HistogramLUTItem()
            self.histogram_layout.addItem(self.histogram)
            self.histogram.gradient.loadPreset("flame")
            #self.histogram.setHistogramRange(-50, 0)
            #self.histogram.setLevels(-50, 0)

    def update_plot(self, data_storage):
        """Update waterfall plot"""
        self.counter += 1

        # Create waterfall image on first run
        # scale_x = (data_storage.x[-1] - data_storage.x[0]) / (len(data_storage.history.buffer[0]) - 1)
        # self.waterfallImg.setTransform(QtGui.QTransform().scale(scale_x, 1))
        if self.counter == 1:
            self.waterfallImg = pg.ImageItem()
            self.plot.clear()
            self.plot.addItem(self.waterfallImg)
        self.waterfallImg.setTransform(QtGui.QTransform().scale(
            (data_storage.x[-1] - data_storage.x[0]) / (len(data_storage.history.buffer[0]) - 1), 1
        ))

        # Roll down one and replace leading edge with new data
        self.waterfallImg.setImage(data_storage.history.buffer[-self.counter:].T,
                                   autoLevels=False, autoRange=False)

        # Move waterfall image to always start at 0
        self.waterfallImg.setPos(
            data_storage.x[0],
            -self.counter if self.counter < self.history_size else -self.history_size
        )

        # Link histogram widget to waterfall image on first run
        # (must be done after first data is received or else levels would be wrong)
        if self.counter == 1 and self.histogram_layout:
            self.histogram.setImageItem(self.waterfallImg)



    def clear_plot(self):
        """Clear waterfall plot"""
        self.counter = 0

    def recalculate_plot(self, data_storage):
        """Recalculate waterfall plot"""
        if data_storage.x is None:
            return

        self.waterfallImg.setImage(data_storage.history.buffer[-self.counter:].T,
                                   autoLevels=False, autoRange=False)
        self.waterfallImg.setPos(
            data_storage.x[0],
            -self.counter if self.counter < self.history_size else -self.history_size
        )
        self.histogram.setImageItem(self.waterfallImg)


class ConstellationPlotWidget:
    """Plot widget for displaying IQ constellation diagram"""
    def __init__(self, layout):
        if not isinstance(layout, pg.GraphicsLayoutWidget):
            raise ValueError("layout must be instance of pyqtgraph.GraphicsLayoutWidget")

        self.layout = layout
        self.create_plot()

    def create_plot(self):
        """Create the constellation plot"""
        self.plot = self.layout.addPlot(row=0, col=0, title="Constellation Diagram")
        self.plot.setLabel("left", "Quadrature Amplitude")
        self.plot.setLabel("bottom", "In-phase Amplitude")
        self.plot.setXRange(-2, 2)
        self.plot.setYRange(-2, 2)
        self.plot.showGrid(x=True, y=True)
        self.plot.setAspectLocked(True)  # Ensure the aspect ratio remains square

        # Create scatter plot item
        self.scatter = pg.ScatterPlotItem(size=2, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 0, 120))
        self.plot.addItem(self.scatter)


    def update_plot(self, iq_data):
        """Update the constellation plot with new IQ data"""

        if iq_data is None or len(iq_data) == 0:
            print("⚠️ Aucune donnée reçue pour la constellation.")
            return

        # Convertir iq_data en numpy array pour éviter les erreurs
        iq_data = np.asarray(iq_data)

        # Vérification des NaN AVANT traitement
        if np.isnan(iq_data).any():
            print("⚠️ IQ Data contient déjà des NaN avant traitement.")

        # Extraction des parties I et Q avec un sous-échantillonnage
        i_data = iq_data.real[::10]
        q_data = iq_data.imag[::10]

        # Vérification et suppression des NaN
        mask = ~np.isnan(i_data) & ~np.isnan(q_data)

        # Vérifier si le mask est vide
        if not np.any(mask):
            print("⚠️ Masque de suppression NaN vide, aucunes données valides.")
            return

        i_data = i_data[mask]
        q_data = q_data[mask]

        # Vérification si les données sont encore valides après filtrage
        if len(i_data) == 0 or len(q_data) == 0:
            print("⚠️ Toutes les valeurs IQ sont NaN ou invalides après filtrage.")
            return

        # Mise à jour du scatter plot
        self.scatter.setData(i_data, q_data)



