"""
Cross-Spectrum Analysis Window for SpectralEdge.

This module provides a GUI window for cross-spectral density (CSD),
coherence, and transfer function analysis between two channels.

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QGroupBox, QGridLayout,
    QTabWidget, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from typing import List, Tuple, Optional, Dict

from spectral_edge.core.psd import (
    calculate_csd, calculate_coherence, calculate_transfer_function,
    calculate_psd_welch
)
from spectral_edge.utils.message_box import show_warning, show_critical


class CrossSpectrumWindow(QMainWindow):
    """
    Window for cross-spectral analysis between two channels.

    This window provides:
    - Cross-Spectral Density (CSD) magnitude and phase
    - Coherence analysis with significance threshold
    - Transfer function (H1 estimator) magnitude and phase
    - Individual PSDs of both channels for reference

    Attributes
    ----------
    channels_data : list
        List of (name, signal, unit, flight_name) tuples for available channels.
    sample_rate : float
        Sample rate of the data.
    """

    def __init__(
        self,
        channels_data: List[Tuple[str, np.ndarray, str, str]],
        sample_rate: float,
        window_type: str = 'hann',
        df: float = 1.0,
        overlap_percent: int = 50,
        freq_min: float = 20.0,
        freq_max: float = 2000.0,
        parent=None
    ):
        """
        Initialize the Cross-Spectrum Analysis window.

        Parameters
        ----------
        channels_data : list
            List of (name, signal, unit, flight_name) tuples.
        sample_rate : float
            Sample rate in Hz.
        window_type : str, optional
            Window function for spectral analysis.
        df : float, optional
            Frequency resolution in Hz.
        overlap_percent : int, optional
            Overlap percentage for Welch's method.
        freq_min : float, optional
            Minimum frequency for display.
        freq_max : float, optional
            Maximum frequency for display.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)

        self.channels_data = channels_data
        self.sample_rate = sample_rate
        self.window_type = window_type
        self.df = df
        self.overlap_percent = overlap_percent
        self.freq_min = freq_min
        self.freq_max = freq_max

        # Results storage
        self.frequencies = None
        self.coherence = None
        self.csd_magnitude = None
        self.csd_phase = None
        self.tf_magnitude = None
        self.tf_phase = None
        self.psd_ref = None
        self.psd_resp = None

        # Window setup
        self.setWindowTitle("SpectralEdge - Cross-Spectrum Analysis")
        self.setMinimumSize(1200, 800)

        # Apply styling
        self._apply_styling()

        # Create UI
        self._create_ui()

        # Initial calculation if we have at least 2 channels
        if len(self.channels_data) >= 2:
            self._calculate()

    def _apply_styling(self):
        """Apply aerospace-inspired styling."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1f2e;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 2px solid #4a5568;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d4758;
                border: 2px solid #5a6578;
            }
            QPushButton:pressed {
                background-color: #1d2738;
            }
            QGroupBox {
                color: #e0e0e0;
                border: 2px solid #4a5568;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 5px;
                min-height: 25px;
            }
            QTabWidget::pane {
                border: 2px solid #4a5568;
                border-radius: 5px;
                background-color: #1a1f2e;
            }
            QTabBar::tab {
                background-color: #2d3748;
                color: #9ca3af;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #1a1f2e;
                color: #60a5fa;
                font-weight: bold;
            }
            QCheckBox {
                color: #e0e0e0;
            }
        """)

    def _create_ui(self):
        """Create the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel: Controls
        left_panel = self._create_control_panel()
        main_layout.addWidget(left_panel, stretch=1)

        # Right panel: Plots
        right_panel = self._create_plot_panel()
        main_layout.addWidget(right_panel, stretch=4)

    def _create_control_panel(self):
        """Create the control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title
        title = QLabel("Cross-Spectrum Analysis")
        title_font = QFont("Arial", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #60a5fa;")
        layout.addWidget(title)

        # Channel selection group
        channel_group = QGroupBox("Channel Selection")
        channel_layout = QGridLayout()

        # Reference channel
        channel_layout.addWidget(QLabel("Reference:"), 0, 0)
        self.ref_combo = QComboBox()
        for name, _, unit, flight in self.channels_data:
            display_name = f"{flight} - {name}" if flight else name
            if unit:
                display_name += f" ({unit})"
            self.ref_combo.addItem(display_name)
        if len(self.channels_data) > 0:
            self.ref_combo.setCurrentIndex(0)
        channel_layout.addWidget(self.ref_combo, 0, 1)

        # Response channel
        channel_layout.addWidget(QLabel("Response:"), 1, 0)
        self.resp_combo = QComboBox()
        for name, _, unit, flight in self.channels_data:
            display_name = f"{flight} - {name}" if flight else name
            if unit:
                display_name += f" ({unit})"
            self.resp_combo.addItem(display_name)
        if len(self.channels_data) > 1:
            self.resp_combo.setCurrentIndex(1)
        channel_layout.addWidget(self.resp_combo, 1, 1)

        channel_group.setLayout(channel_layout)
        layout.addWidget(channel_group)

        # Parameters group
        param_group = QGroupBox("Parameters")
        param_layout = QGridLayout()

        # Frequency resolution
        param_layout.addWidget(QLabel("Δf (Hz):"), 0, 0)
        self.df_spin = QDoubleSpinBox()
        self.df_spin.setRange(0.01, 100)
        self.df_spin.setValue(self.df)
        self.df_spin.setDecimals(2)
        param_layout.addWidget(self.df_spin, 0, 1)

        # Overlap
        param_layout.addWidget(QLabel("Overlap (%):"), 1, 0)
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(self.overlap_percent)
        param_layout.addWidget(self.overlap_spin, 1, 1)

        # Frequency range
        param_layout.addWidget(QLabel("Freq Min (Hz):"), 2, 0)
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0.1, 10000)
        self.freq_min_spin.setValue(self.freq_min)
        param_layout.addWidget(self.freq_min_spin, 2, 1)

        param_layout.addWidget(QLabel("Freq Max (Hz):"), 3, 0)
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(1, 100000)
        self.freq_max_spin.setValue(self.freq_max)
        param_layout.addWidget(self.freq_max_spin, 3, 1)

        param_group.setLayout(param_layout)
        layout.addWidget(param_group)

        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout()

        self.show_threshold_checkbox = QCheckBox("Show Coherence Threshold (0.9)")
        self.show_threshold_checkbox.setChecked(True)
        self.show_threshold_checkbox.stateChanged.connect(self._update_plots)
        display_layout.addWidget(self.show_threshold_checkbox)

        self.log_freq_checkbox = QCheckBox("Log Frequency Axis")
        self.log_freq_checkbox.setChecked(True)
        self.log_freq_checkbox.stateChanged.connect(self._update_plots)
        display_layout.addWidget(self.log_freq_checkbox)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Calculate button
        calc_button = QPushButton("Calculate")
        calc_button.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
        """)
        calc_button.clicked.connect(self._calculate)
        layout.addWidget(calc_button)

        # Results display
        self.results_label = QLabel("")
        self.results_label.setWordWrap(True)
        self.results_label.setStyleSheet("color: #9ca3af; font-size: 10px;")
        layout.addWidget(self.results_label)

        layout.addStretch()

        return panel

    def _create_plot_panel(self):
        """Create the plot panel with tabs."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Tab widget for different views
        self.tab_widget = QTabWidget()

        # Tab 1: Coherence
        coherence_widget = QWidget()
        coherence_layout = QVBoxLayout(coherence_widget)
        self.coherence_plot = pg.PlotWidget()
        self._setup_plot(self.coherence_plot, "Coherence", "Frequency (Hz)", "Coherence")
        self.coherence_plot.setYRange(0, 1.1)
        coherence_layout.addWidget(self.coherence_plot)
        self.tab_widget.addTab(coherence_widget, "Coherence")

        # Tab 2: CSD
        csd_widget = QWidget()
        csd_layout = QVBoxLayout(csd_widget)

        # CSD magnitude
        self.csd_mag_plot = pg.PlotWidget()
        self._setup_plot(self.csd_mag_plot, "CSD Magnitude", "", "Magnitude")
        csd_layout.addWidget(self.csd_mag_plot, stretch=1)

        # CSD phase
        self.csd_phase_plot = pg.PlotWidget()
        self._setup_plot(self.csd_phase_plot, "CSD Phase", "Frequency (Hz)", "Phase (deg)")
        self.csd_phase_plot.setYRange(-180, 180)
        csd_layout.addWidget(self.csd_phase_plot, stretch=1)

        self.tab_widget.addTab(csd_widget, "CSD")

        # Tab 3: Transfer Function
        tf_widget = QWidget()
        tf_layout = QVBoxLayout(tf_widget)

        # TF magnitude
        self.tf_mag_plot = pg.PlotWidget()
        self._setup_plot(self.tf_mag_plot, "Transfer Function Magnitude", "", "Magnitude")
        tf_layout.addWidget(self.tf_mag_plot, stretch=1)

        # TF phase
        self.tf_phase_plot = pg.PlotWidget()
        self._setup_plot(self.tf_phase_plot, "Transfer Function Phase", "Frequency (Hz)", "Phase (deg)")
        self.tf_phase_plot.setYRange(-180, 180)
        tf_layout.addWidget(self.tf_phase_plot, stretch=1)

        self.tab_widget.addTab(tf_widget, "Transfer Function")

        # Tab 4: PSDs
        psd_widget = QWidget()
        psd_layout = QVBoxLayout(psd_widget)
        self.psd_plot = pg.PlotWidget()
        self._setup_plot(self.psd_plot, "Power Spectral Density", "Frequency (Hz)", "PSD")
        self.psd_plot.setLogMode(x=True, y=True)

        # Add legend with border and background
        self.psd_legend = self.psd_plot.addLegend(offset=(10, 10))
        self.psd_legend.setBrush(pg.mkBrush(26, 31, 46, 200))  # Semi-transparent dark background
        self.psd_legend.setPen(pg.mkPen(74, 85, 104, 255))  # Subtle border

        psd_layout.addWidget(self.psd_plot)
        self.tab_widget.addTab(psd_widget, "PSDs")

        layout.addWidget(self.tab_widget)

        return panel

    def _setup_plot(self, plot_widget, title: str, x_label: str, y_label: str):
        """Configure a plot widget with standard styling."""
        plot_widget.setBackground('#1a1f2e')
        plot_widget.setTitle(title, color='#60a5fa', size='12pt')
        if x_label:
            plot_widget.setLabel('bottom', x_label, color='#e0e0e0', size='11pt')
        if y_label:
            plot_widget.setLabel('left', y_label, color='#e0e0e0', size='11pt')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        plot_widget.setMouseEnabled(x=True, y=True)

    def _calculate(self):
        """Calculate cross-spectral analysis."""
        if len(self.channels_data) < 2:
            show_warning(self, "Insufficient Data",
                        "At least two channels are required for cross-spectrum analysis.")
            return

        ref_idx = self.ref_combo.currentIndex()
        resp_idx = self.resp_combo.currentIndex()

        if ref_idx == resp_idx:
            show_warning(self, "Same Channel Selected",
                        "Please select two different channels for cross-spectrum analysis.")
            return

        try:
            # Get signals
            ref_name, ref_signal, ref_unit, _ = self.channels_data[ref_idx]
            resp_name, resp_signal, resp_unit, _ = self.channels_data[resp_idx]

            # Ensure signals have the same length
            min_len = min(len(ref_signal), len(resp_signal))
            ref_signal = ref_signal[:min_len]
            resp_signal = resp_signal[:min_len]

            # Get parameters
            df = self.df_spin.value()
            overlap = self.overlap_spin.value()
            nperseg = int(self.sample_rate / df)
            noverlap = int(nperseg * overlap / 100)

            # Calculate coherence
            self.frequencies, self.coherence = calculate_coherence(
                ref_signal, resp_signal, self.sample_rate,
                window=self.window_type, df=df
            )

            # Calculate CSD
            _, csd_complex = calculate_csd(
                ref_signal, resp_signal, self.sample_rate,
                window=self.window_type, df=df
            )
            self.csd_magnitude = np.abs(csd_complex)
            self.csd_phase = np.angle(csd_complex, deg=True)

            # Calculate transfer function
            _, self.tf_magnitude, self.tf_phase = calculate_transfer_function(
                ref_signal, resp_signal, self.sample_rate,
                window=self.window_type, df=df
            )

            # Calculate individual PSDs
            _, self.psd_ref = calculate_psd_welch(
                ref_signal, self.sample_rate, window=self.window_type, df=df
            )
            _, self.psd_resp = calculate_psd_welch(
                resp_signal, self.sample_rate, window=self.window_type, df=df
            )

            # Calculate statistics
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()
            mask = (self.frequencies >= freq_min) & (self.frequencies <= freq_max)

            if np.any(mask):
                mean_coherence = np.mean(self.coherence[mask])
                max_coherence = np.max(self.coherence[mask])
                freq_at_max = self.frequencies[mask][np.argmax(self.coherence[mask])]

                self.results_label.setText(
                    f"Results ({freq_min:.0f}-{freq_max:.0f} Hz):\n"
                    f"Mean Coherence: {mean_coherence:.3f}\n"
                    f"Max Coherence: {max_coherence:.3f} at {freq_at_max:.1f} Hz"
                )

            # Update plots
            self._update_plots()

        except Exception as e:
            show_critical(self, "Calculation Error", f"Failed to calculate: {str(e)}")

    def _set_frequency_ticks(self, plot_widget):
        """Set frequency axis ticks to only show powers of 10 for log mode."""
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()

        # Find all powers of 10 within the range
        min_exp = int(np.floor(np.log10(freq_min)))
        max_exp = int(np.ceil(np.log10(freq_max)))

        tick_values = []
        tick_labels = []
        for exp in range(min_exp, max_exp + 1):
            freq = 10 ** exp
            if freq_min <= freq <= freq_max:
                tick_values.append(np.log10(freq))
                tick_labels.append(str(int(freq)))

        # Set the ticks on the bottom axis
        bottom_axis = plot_widget.getPlotItem().getAxis('bottom')
        bottom_axis.setTicks([[(val, label) for val, label in zip(tick_values, tick_labels)]])

    def _reset_frequency_ticks(self, plot_widget):
        """Reset frequency axis ticks to default (auto) for linear mode."""
        bottom_axis = plot_widget.getPlotItem().getAxis('bottom')
        bottom_axis.setTicks(None)  # Reset to automatic tick generation

    def _update_plots(self):
        """Update all plots with current results."""
        if self.frequencies is None:
            return

        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        mask = (self.frequencies >= freq_min) & (self.frequencies <= freq_max)

        if not np.any(mask):
            return

        freqs = self.frequencies[mask]
        log_mode = self.log_freq_checkbox.isChecked()

        # Get channel names for titles
        ref_idx = self.ref_combo.currentIndex()
        resp_idx = self.resp_combo.currentIndex()
        ref_name = self.channels_data[ref_idx][0]
        resp_name = self.channels_data[resp_idx][0]

        # Update coherence plot
        self.coherence_plot.clear()
        self.coherence_plot.setLogMode(x=log_mode, y=False)
        self.coherence_plot.plot(
            freqs, self.coherence[mask],
            pen=pg.mkPen('#60a5fa', width=2),
            name="Coherence"
        )
        # Add threshold line
        if self.show_threshold_checkbox.isChecked():
            threshold_line = pg.InfiniteLine(
                pos=0.9, angle=0,
                pen=pg.mkPen('#ef4444', width=1, style=Qt.PenStyle.DashLine),
                label="0.9 threshold"
            )
            self.coherence_plot.addItem(threshold_line)
        self.coherence_plot.setYRange(0, 1.1)
        if log_mode:
            self._set_frequency_ticks(self.coherence_plot)
        else:
            self._reset_frequency_ticks(self.coherence_plot)

        # Update CSD plots
        self.csd_mag_plot.clear()
        self.csd_mag_plot.setLogMode(x=log_mode, y=True)
        self.csd_mag_plot.plot(
            freqs, self.csd_magnitude[mask],
            pen=pg.mkPen('#10b981', width=2)
        )
        # Disable y-axis auto-scaling to show true values
        self.csd_mag_plot.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        if log_mode:
            self._set_frequency_ticks(self.csd_mag_plot)
        else:
            self._reset_frequency_ticks(self.csd_mag_plot)

        self.csd_phase_plot.clear()
        self.csd_phase_plot.setLogMode(x=log_mode, y=False)
        self.csd_phase_plot.plot(
            freqs, self.csd_phase[mask],
            pen=pg.mkPen('#f59e0b', width=2)
        )
        self.csd_phase_plot.setYRange(-180, 180)
        if log_mode:
            self._set_frequency_ticks(self.csd_phase_plot)
        else:
            self._reset_frequency_ticks(self.csd_phase_plot)

        # Update transfer function plots with channel-specific titles
        self.tf_mag_plot.clear()
        self.tf_mag_plot.setLogMode(x=log_mode, y=True)
        self.tf_mag_plot.setTitle(
            f"Transfer Function Magnitude ({resp_name}/{ref_name})",
            color='#60a5fa', size='12pt'
        )
        self.tf_mag_plot.plot(
            freqs, self.tf_magnitude[mask],
            pen=pg.mkPen('#8b5cf6', width=2)
        )
        if log_mode:
            self._set_frequency_ticks(self.tf_mag_plot)
        else:
            self._reset_frequency_ticks(self.tf_mag_plot)

        self.tf_phase_plot.clear()
        self.tf_phase_plot.setLogMode(x=log_mode, y=False)
        self.tf_phase_plot.setTitle(
            f"Transfer Function Phase ({resp_name}/{ref_name})",
            color='#60a5fa', size='12pt'
        )
        self.tf_phase_plot.plot(
            freqs, self.tf_phase[mask],
            pen=pg.mkPen('#ec4899', width=2)
        )
        self.tf_phase_plot.setYRange(-180, 180)
        if log_mode:
            self._set_frequency_ticks(self.tf_phase_plot)
        else:
            self._reset_frequency_ticks(self.tf_phase_plot)

        # Update PSD plot
        self.psd_plot.clear()

        self.psd_plot.plot(
            freqs, self.psd_ref[mask],
            pen=pg.mkPen('#60a5fa', width=2),
            name=f"Reference: {ref_name}"
        )
        self.psd_plot.plot(
            freqs, self.psd_resp[mask],
            pen=pg.mkPen('#10b981', width=2),
            name=f"Response: {resp_name}"
        )
        # Disable y-axis auto-scaling to show true values
        self.psd_plot.getPlotItem().getAxis('left').enableAutoSIPrefix(False)
        # PSD plot is always in log mode, so always set frequency ticks
        self._set_frequency_ticks(self.psd_plot)
