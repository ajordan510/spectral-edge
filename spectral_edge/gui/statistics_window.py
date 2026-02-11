"""
Statistics Analysis GUI for SpectralEdge.

This module provides statistical analysis of time series data including:
- Probability Density Function (PDF) with standard distribution overlays
- Running statistics (mean, skewness, kurtosis)
- Standard limits for random and sinusoidal signals
- Channel selection and management
- Report generation capability

Designed to be modular for reuse with other tools (SPL, SRS, etc.).

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QGroupBox, QGridLayout, QTabWidget, QScrollArea, QApplication,
    QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from scipy import stats
from scipy.ndimage import uniform_filter1d
from typing import List, Tuple, Optional, Dict

from spectral_edge.utils.message_box import show_information, show_warning, show_critical
from spectral_edge.utils.report_generator import ReportGenerator, export_plot_to_image, PPTX_AVAILABLE
from spectral_edge.utils.signal_conditioning import build_processing_note
from spectral_edge.utils.theme import apply_context_menu_style
from spectral_edge.utils.statistics_overlays import fit_rayleigh_from_signal, build_rayleigh_curve
from spectral_edge.utils.plot_theme import get_watermark_text


class StatisticsCalculationThread(QThread):
    """Background thread for statistics calculation."""
    finished = pyqtSignal(dict, dict)  # pdf_data, running_stats
    progress = pyqtSignal(int, str)  # percent, message
    error = pyqtSignal(str)

    def __init__(self, channels_data, channel_selection, n_bins, window_seconds, sample_rate):
        super().__init__()
        self.channels_data = channels_data
        self.channel_selection = channel_selection
        self.n_bins = n_bins
        self.window_seconds = window_seconds
        self.sample_rate = sample_rate

    def run(self):
        try:
            pdf_data = {}
            running_stats = {}

            selected_channels = [(i, ch) for i, ch in enumerate(self.channels_data)
                                 if self.channel_selection[i]]
            total = len(selected_channels)

            for idx, (i, (name, signal, unit, _)) in enumerate(selected_channels):
                self.progress.emit(int(100 * idx / max(total, 1)), f"Processing {name}...")

                # Calculate PDF (fast)
                counts, bin_edges = np.histogram(signal, bins=self.n_bins, density=True)
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

                mean = np.mean(signal)
                std = np.std(signal)

                pdf_data[name] = {
                    'bins': bin_centers,
                    'counts': counts,
                    'mean': mean,
                    'std': std,
                    'unit': unit
                }
                rayleigh_scale, rayleigh_x_max = fit_rayleigh_from_signal(signal)
                pdf_data[name]["rayleigh_scale"] = rayleigh_scale
                pdf_data[name]["rayleigh_x_max"] = rayleigh_x_max

                # Calculate running statistics using optimized uniform_filter1d
                window_samples = int(self.window_seconds * self.sample_rate)
                window_samples = max(10, window_samples)

                n = len(signal)
                if n > window_samples:
                    # Use uniform_filter1d for O(n) running mean (much faster than convolve)
                    signal_float = signal.astype(np.float64)
                    running_mean = uniform_filter1d(signal_float, size=window_samples, mode='nearest')

                    # Running std using uniform_filter1d
                    running_sq = uniform_filter1d(signal_float**2, size=window_samples, mode='nearest')
                    running_std = np.sqrt(np.maximum(running_sq - running_mean**2, 0))

                    # Downsample for display (keep max 5000 points)
                    max_points = 5000
                    if len(running_mean) > max_points:
                        step = len(running_mean) // max_points
                        running_mean = running_mean[::step]
                        running_std = running_std[::step]
                        time = np.arange(len(running_mean)) * step / self.sample_rate
                    else:
                        time = np.arange(len(running_mean)) / self.sample_rate

                    # Calculate sampled skewness and kurtosis (limit to 200 points for speed)
                    n_samples = min(200, len(signal) // window_samples)
                    if n_samples > 0:
                        sample_step = len(signal) // n_samples
                        running_skewness = np.zeros(n_samples)
                        running_kurtosis = np.zeros(n_samples)
                        skewness_time = np.zeros(n_samples)

                        for j in range(n_samples):
                            start_idx = j * sample_step
                            end_idx = min(start_idx + window_samples, len(signal))
                            window = signal[start_idx:end_idx]
                            if len(window) > 10:
                                running_skewness[j] = stats.skew(window)
                                running_kurtosis[j] = stats.kurtosis(window)
                            skewness_time[j] = start_idx / self.sample_rate
                    else:
                        running_skewness = np.array([0])
                        running_kurtosis = np.array([0])
                        skewness_time = np.array([0])

                    running_stats[name] = {
                        'time': time,
                        'mean': running_mean,
                        'std': running_std,
                        'skewness_time': skewness_time,
                        'skewness': running_skewness,
                        'kurtosis': running_kurtosis,
                        'unit': unit
                    }

                # Overall statistics (use faster numpy where possible)
                rms = np.sqrt(np.mean(signal**2))
                crest_factor = np.max(np.abs(signal)) / rms if rms > 1e-12 else 0.0

                # For large signals, sample for skewness/kurtosis
                if len(signal) > 100000:
                    sample_indices = np.random.choice(len(signal), 100000, replace=False)
                    signal_sample = signal[sample_indices]
                    skewness = stats.skew(signal_sample)
                    kurtosis = stats.kurtosis(signal_sample)
                else:
                    skewness = stats.skew(signal)
                    kurtosis = stats.kurtosis(signal)

                pdf_data[name]['overall'] = {
                    'mean': mean,
                    'std': std,
                    'skewness': skewness,
                    'kurtosis': kurtosis,
                    'min': np.min(signal),
                    'max': np.max(signal),
                    'rms': rms,
                    'crest_factor': crest_factor
                }

            self.progress.emit(100, "Complete")
            self.finished.emit(pdf_data, running_stats)

        except Exception as e:
            self.error.emit(str(e))


class StatisticsWindow(QMainWindow):
    """
    Statistics Analysis window for time series data.

    Provides:
    - PDF visualization with standard distribution overlays
    - Running statistics (mean, std, skewness, kurtosis)
    - Standard limits for random/sinusoidal signals
    - Channel selection
    - Report generation
    """

    def __init__(
        self,
        channels_data: List[Tuple[str, np.ndarray, str, str]],
        sample_rate: float,
        parent=None,
        processing_note: str = "",
        processing_flags: Optional[Dict[str, object]] = None,
    ):
        """
        Initialize the Statistics Analysis window.

        Parameters
        ----------
        channels_data : list
            List of (name, signal, unit, flight_name) tuples.
        sample_rate : float
            Sample rate in Hz.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)

        self.channels_data = channels_data
        self.sample_rate = sample_rate
        self.channel_names = [ch[0] for ch in channels_data]
        self.channel_units = [ch[2] for ch in channels_data]
        self.processing_note = processing_note or build_processing_note(
            filter_settings={"enabled": False},
            remove_mean=False,
            mean_window_seconds=1.0,
        )
        self.processing_flags = processing_flags or {}

        # Channel selection checkboxes
        self.channel_checkboxes = []

        # Storage for calculated statistics
        self.pdf_data = {}  # {channel: (bins, counts, fitted_params)}
        self.running_stats = {}  # {channel: {mean, std, skewness, kurtosis}}

        # Background calculation thread
        self.calc_thread = None

        # Distribution overlay options
        self.show_normal = True
        self.show_rayleigh = False

        # Set window properties
        self.setWindowTitle("SpectralEdge - Statistics Analysis")
        self.setMinimumSize(1400, 900)

        # Apply styling
        self._apply_styling()

        # Create UI
        self._create_ui()

        # Schedule initial calculation after event loop starts (non-blocking)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._calculate_statistics)

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
            }
            QScrollArea {
                background-color: #1a1f2e;
                border: 1px solid #4a5568;
                border-radius: 4px;
            }
            QWidget#channelWidget {
                background-color: #1a1f2e;
            }
            QCheckBox {
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a5568;
                border-radius: 3px;
                background-color: #2d3748;
            }
            QCheckBox::indicator:checked {
                background-color: #60a5fa;
                border-color: #60a5fa;
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
        main_layout.addWidget(right_panel, stretch=3)

    def _create_control_panel(self):
        """Create the control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title
        title = QLabel("Statistics Analysis")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #60a5fa;")
        layout.addWidget(title)

        self.conditioning_note_label = QLabel(f"Signal Conditioning: {self.processing_note}")
        self.conditioning_note_label.setWordWrap(True)
        self.conditioning_note_label.setStyleSheet(
            "color: #cbd5e1; font-size: 10pt; padding: 6px; background-color: #252d3d; border-radius: 4px;"
        )
        layout.addWidget(self.conditioning_note_label)

        # Channel selection
        channel_group = self._create_channel_group()
        layout.addWidget(channel_group)

        # PDF options
        pdf_group = self._create_pdf_options_group()
        layout.addWidget(pdf_group)

        # Running stats options
        stats_group = self._create_stats_options_group()
        layout.addWidget(stats_group)

        # Standard limits
        limits_group = self._create_limits_group()
        layout.addWidget(limits_group)

        # Calculate button
        calc_button = QPushButton("Recalculate Statistics")
        calc_button.clicked.connect(self._calculate_statistics)
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
        layout.addWidget(calc_button)

        # Report button
        report_button = QPushButton("Generate Report")
        report_button.clicked.connect(self._generate_report)
        if not PPTX_AVAILABLE:
            report_button.setEnabled(False)
            report_button.setToolTip("python-pptx not installed")
        layout.addWidget(report_button)

        layout.addStretch()

        return panel

    def _create_channel_group(self):
        """Create channel selection group."""
        group = QGroupBox("Channel Selection")
        layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)

        channel_widget = QWidget()
        channel_widget.setObjectName("channelWidget")
        channel_layout = QVBoxLayout(channel_widget)
        channel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Channel colors
        colors = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#f472b6']

        for i, (name, _, unit, _) in enumerate(self.channels_data):
            checkbox = QCheckBox(f"{name} ({unit})" if unit else name)
            checkbox.setChecked(i == 0)  # First channel selected by default
            checkbox.setStyleSheet(f"color: {colors[i % len(colors)]};")
            checkbox.stateChanged.connect(self._on_channel_changed)
            channel_layout.addWidget(checkbox)
            self.channel_checkboxes.append(checkbox)

        scroll.setWidget(channel_widget)
        layout.addWidget(scroll)

        group.setLayout(layout)
        return group

    def _create_pdf_options_group(self):
        """Create PDF options group."""
        group = QGroupBox("PDF Options")
        layout = QVBoxLayout()

        # Number of bins
        bins_layout = QHBoxLayout()
        bins_layout.addWidget(QLabel("Number of Bins:"))
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(10, 500)
        self.bins_spin.setValue(50)
        self.bins_spin.valueChanged.connect(self._on_parameter_changed)
        bins_layout.addWidget(self.bins_spin)
        layout.addLayout(bins_layout)

        # Distribution overlays
        layout.addWidget(QLabel("Distribution Overlays:"))

        self.normal_checkbox = QCheckBox("Normal (Gaussian)")
        self.normal_checkbox.setChecked(True)
        self.normal_checkbox.stateChanged.connect(self._on_overlay_changed)
        layout.addWidget(self.normal_checkbox)

        self.rayleigh_checkbox = QCheckBox("Rayleigh")
        self.rayleigh_checkbox.setChecked(False)
        self.rayleigh_checkbox.stateChanged.connect(self._on_overlay_changed)
        layout.addWidget(self.rayleigh_checkbox)

        self.uniform_checkbox = QCheckBox("Uniform")
        self.uniform_checkbox.setChecked(False)
        self.uniform_checkbox.stateChanged.connect(self._on_overlay_changed)
        layout.addWidget(self.uniform_checkbox)

        group.setLayout(layout)
        return group

    def _create_stats_options_group(self):
        """Create running statistics options group."""
        group = QGroupBox("Running Statistics")
        layout = QVBoxLayout()

        # Window size for running stats
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Window Size (s):"))
        self.window_spin = QDoubleSpinBox()
        self.window_spin.setRange(0.1, 10.0)
        self.window_spin.setValue(1.0)
        self.window_spin.setSingleStep(0.1)
        self.window_spin.valueChanged.connect(self._on_parameter_changed)
        window_layout.addWidget(self.window_spin)
        layout.addLayout(window_layout)

        # Statistics to display
        layout.addWidget(QLabel("Display:"))

        self.show_mean_checkbox = QCheckBox("Mean")
        self.show_mean_checkbox.setChecked(True)
        self.show_mean_checkbox.stateChanged.connect(self._update_running_stats_plot)
        layout.addWidget(self.show_mean_checkbox)

        self.show_std_checkbox = QCheckBox("Standard Deviation")
        self.show_std_checkbox.setChecked(True)
        self.show_std_checkbox.stateChanged.connect(self._update_running_stats_plot)
        layout.addWidget(self.show_std_checkbox)

        self.show_skewness_checkbox = QCheckBox("Skewness")
        self.show_skewness_checkbox.setChecked(False)
        self.show_skewness_checkbox.stateChanged.connect(self._update_running_stats_plot)
        layout.addWidget(self.show_skewness_checkbox)

        self.show_kurtosis_checkbox = QCheckBox("Kurtosis")
        self.show_kurtosis_checkbox.setChecked(False)
        self.show_kurtosis_checkbox.stateChanged.connect(self._update_running_stats_plot)
        layout.addWidget(self.show_kurtosis_checkbox)

        group.setLayout(layout)
        return group

    def _create_limits_group(self):
        """Create standard limits group."""
        group = QGroupBox("Standard Limits")
        layout = QVBoxLayout()

        desc = QLabel("Reference lines for signal characterization:")
        desc.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.random_limit_checkbox = QCheckBox("Random Signal (±3σ)")
        self.random_limit_checkbox.setChecked(False)
        self.random_limit_checkbox.setToolTip("Show ±3 sigma limits for Gaussian random signals")
        self.random_limit_checkbox.stateChanged.connect(self._update_plots)
        layout.addWidget(self.random_limit_checkbox)

        self.sine_limit_checkbox = QCheckBox("Sinusoidal (±√2·RMS)")
        self.sine_limit_checkbox.setChecked(False)
        self.sine_limit_checkbox.setToolTip("Show peak limits for pure sinusoidal signals")
        self.sine_limit_checkbox.stateChanged.connect(self._update_plots)
        layout.addWidget(self.sine_limit_checkbox)

        group.setLayout(layout)
        return group

    def _create_plot_panel(self):
        """Create the plot panel with tabs."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Create tabbed interface
        self.tab_widget = QTabWidget()

        # Tab 1: PDF
        pdf_widget = QWidget()
        pdf_layout = QVBoxLayout(pdf_widget)
        self.pdf_plot = pg.PlotWidget()
        self.pdf_plot.setBackground('#1a1f2e')
        apply_context_menu_style(self.pdf_plot)
        self.pdf_plot.setLabel('left', 'Probability Density', color='#e0e0e0')
        self.pdf_plot.setLabel('bottom', 'Value', color='#e0e0e0')
        self.pdf_plot.setTitle("Probability Density Function", color='#60a5fa')
        self.pdf_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pdf_plot.addLegend(offset=(10, 10))
        pdf_layout.addWidget(self.pdf_plot)
        self.tab_widget.addTab(pdf_widget, "PDF")

        # Tab 2: Running Statistics
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        self.running_stats_plot = pg.PlotWidget()
        self.running_stats_plot.setBackground('#1a1f2e')
        apply_context_menu_style(self.running_stats_plot)
        self.running_stats_plot.setLabel('left', 'Value', color='#e0e0e0')
        self.running_stats_plot.setLabel('bottom', 'Time', units='s', color='#e0e0e0')
        self.running_stats_plot.setTitle("Running Statistics", color='#60a5fa')
        self.running_stats_plot.showGrid(x=True, y=True, alpha=0.3)
        self.running_stats_plot.addLegend(offset=(10, 10))
        stats_layout.addWidget(self.running_stats_plot)
        self.tab_widget.addTab(stats_widget, "Running Stats")

        # Tab 3: Summary Statistics
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        self.summary_label = QLabel("Select channels and click 'Recalculate Statistics'")
        self.summary_label.setStyleSheet("""
            color: #e0e0e0;
            font-family: monospace;
            font-size: 12pt;
            padding: 20px;
            background-color: #252d3d;
            border-radius: 5px;
        """)
        self.summary_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_label)
        self.tab_widget.addTab(summary_widget, "Summary")

        layout.addWidget(self.tab_widget)

        return panel

    def _on_channel_changed(self):
        """Handle channel selection change."""
        self._calculate_statistics()

    def _on_parameter_changed(self):
        """Handle parameter change."""
        self._calculate_statistics()

    def _on_overlay_changed(self):
        """Handle distribution overlay change."""
        self._update_pdf_plot()

    def _calculate_statistics(self):
        """Calculate all statistics for selected channels in background thread."""
        # Stop any running calculation
        if self.calc_thread is not None and self.calc_thread.isRunning():
            self.calc_thread.terminate()
            self.calc_thread.wait()

        # Get channel selection state
        channel_selection = [cb.isChecked() for cb in self.channel_checkboxes]

        # Check if any channel is selected
        if not any(channel_selection):
            self.pdf_data = {}
            self.running_stats = {}
            self._update_plots()
            self._update_summary()
            return

        # Update UI to show calculating
        self.summary_label.setText("Calculating statistics...")
        QApplication.processEvents()

        # Create and start calculation thread
        self.calc_thread = StatisticsCalculationThread(
            channels_data=self.channels_data,
            channel_selection=channel_selection,
            n_bins=self.bins_spin.value(),
            window_seconds=self.window_spin.value(),
            sample_rate=self.sample_rate
        )
        self.calc_thread.finished.connect(self._on_calculation_finished)
        self.calc_thread.progress.connect(self._on_calculation_progress)
        self.calc_thread.error.connect(self._on_calculation_error)
        self.calc_thread.start()

    def _on_calculation_finished(self, pdf_data, running_stats):
        """Handle calculation completion."""
        self.pdf_data = pdf_data
        self.running_stats = running_stats
        self._update_plots()
        self._update_summary()

    def _on_calculation_progress(self, percent, message):
        """Handle calculation progress."""
        self.summary_label.setText(f"Calculating: {message} ({percent}%)")

    def _on_calculation_error(self, error_msg):
        """Handle calculation error."""
        self.summary_label.setText(f"Error: {error_msg}")
        show_warning(self, "Calculation Error", f"Failed to calculate statistics: {error_msg}")

    def _update_plots(self):
        """Update all plots."""
        self._update_pdf_plot()
        self._update_running_stats_plot()

    def _update_pdf_plot(self):
        """Update the PDF plot."""
        self.pdf_plot.clear()

        colors = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#f472b6']

        for i, (name, data) in enumerate(self.pdf_data.items()):
            color = colors[i % len(colors)]

            # Plot histogram
            self.pdf_plot.plot(
                data['bins'],
                data['counts'],
                pen=None,
                symbol='o',
                symbolSize=5,
                symbolBrush=color,
                name=name
            )

            # Plot fitted normal distribution
            if self.normal_checkbox.isChecked():
                x = np.linspace(data['bins'].min(), data['bins'].max(), 200)
                y = stats.norm.pdf(x, data['mean'], data['std'])
                self.pdf_plot.plot(
                    x, y,
                    pen=pg.mkPen(color=color, width=2),
                    name=f"{name} (Normal fit)"
                )

            # Plot Rayleigh distribution
            if self.rayleigh_checkbox.isChecked():
                rayleigh_x, rayleigh_y = build_rayleigh_curve(
                    data.get("rayleigh_scale"),
                    data.get("rayleigh_x_max"),
                    n_points=300,
                )
                if rayleigh_x is not None and rayleigh_y is not None:
                    self.pdf_plot.plot(
                        rayleigh_x,
                        rayleigh_y,
                        pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine),
                        name=f"{name} (Rayleigh)"
                    )

            # Plot uniform distribution
            if self.uniform_checkbox.isChecked():
                x = np.linspace(data['bins'].min(), data['bins'].max(), 200)
                loc = data['mean'] - data['std'] * np.sqrt(3)
                scale = 2 * data['std'] * np.sqrt(3)
                y = stats.uniform.pdf(x, loc=loc, scale=scale)
                self.pdf_plot.plot(
                    x, y,
                    pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DotLine),
                    name=f"{name} (Uniform)"
                )

            # Add standard limits
            if self.random_limit_checkbox.isChecked():
                # ±3σ limits for random signals
                for mult in [-3, 3]:
                    limit = data['mean'] + mult * data['std']
                    self.pdf_plot.addLine(
                        x=limit,
                        pen=pg.mkPen(color='#ef4444', width=1, style=Qt.PenStyle.DashLine)
                    )

            if self.sine_limit_checkbox.isChecked():
                # Peak limits for sinusoidal signals (±√2·RMS)
                rms = data['overall']['rms']
                for mult in [-1, 1]:
                    limit = mult * np.sqrt(2) * rms
                    self.pdf_plot.addLine(
                        x=limit,
                        pen=pg.mkPen(color='#22c55e', width=1, style=Qt.PenStyle.DashLine)
                    )

        # Update axis label with units
        if self.pdf_data:
            first_data = next(iter(self.pdf_data.values()))
            unit = first_data.get('unit', '')
            if unit:
                self.pdf_plot.setLabel('bottom', f'Value ({unit})', color='#e0e0e0')

    def _update_running_stats_plot(self):
        """Update the running statistics plot."""
        self.running_stats_plot.clear()

        colors = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#f472b6']

        for i, (name, data) in enumerate(self.running_stats.items()):
            color = colors[i % len(colors)]

            if self.show_mean_checkbox.isChecked():
                self.running_stats_plot.plot(
                    data['time'],
                    data['mean'],
                    pen=pg.mkPen(color=color, width=2),
                    name=f"{name} Mean"
                )

            if self.show_std_checkbox.isChecked():
                self.running_stats_plot.plot(
                    data['time'],
                    data['std'],
                    pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine),
                    name=f"{name} Std"
                )

            if self.show_skewness_checkbox.isChecked():
                self.running_stats_plot.plot(
                    data['skewness_time'],
                    data['skewness'],
                    pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DotLine),
                    name=f"{name} Skewness"
                )

            if self.show_kurtosis_checkbox.isChecked():
                self.running_stats_plot.plot(
                    data['skewness_time'],
                    data['kurtosis'],
                    pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashDotLine),
                    name=f"{name} Kurtosis"
                )

    def _update_summary(self):
        """Update the summary statistics display."""
        if not self.pdf_data:
            self.summary_label.setText("No channels selected.")
            return

        lines = [
            "=" * 60,
            "STATISTICAL SUMMARY",
            "=" * 60,
            f"Signal Conditioning: {self.processing_note}",
            "",
        ]

        for name, data in self.pdf_data.items():
            overall = data['overall']
            unit = data.get('unit', '')
            unit_str = f" {unit}" if unit else ""

            lines.append(f"Channel: {name}")
            lines.append("-" * 40)
            lines.append(f"  Mean:          {overall['mean']:>12.4e}{unit_str}")
            lines.append(f"  Std Dev:       {overall['std']:>12.4e}{unit_str}")
            lines.append(f"  RMS:           {overall['rms']:>12.4e}{unit_str}")
            lines.append(f"  Min:           {overall['min']:>12.4e}{unit_str}")
            lines.append(f"  Max:           {overall['max']:>12.4e}{unit_str}")
            lines.append(f"  Skewness:      {overall['skewness']:>12.4f}")
            lines.append(f"  Kurtosis:      {overall['kurtosis']:>12.4f}")
            lines.append(f"  Crest Factor:  {overall['crest_factor']:>12.4f}")
            lines.append("")

            # Distribution characterization
            if abs(overall['skewness']) < 0.5 and abs(overall['kurtosis']) < 1:
                char = "Approximately Gaussian"
            elif overall['skewness'] > 1:
                char = "Right-skewed (positive skewness)"
            elif overall['skewness'] < -1:
                char = "Left-skewed (negative skewness)"
            elif overall['kurtosis'] > 1:
                char = "Heavy-tailed (leptokurtic)"
            elif overall['kurtosis'] < -1:
                char = "Light-tailed (platykurtic)"
            else:
                char = "Mixed characteristics"

            lines.append(f"  Distribution:  {char}")
            lines.append("")

        self.summary_label.setText("\n".join(lines))

    def _generate_report(self):
        """Generate a PowerPoint report."""
        if not PPTX_AVAILABLE:
            show_warning(self, "Feature Unavailable",
                        "python-pptx is not installed.")
            return

        if not self.pdf_data:
            show_warning(self, "No Data",
                        "Please select channels and calculate statistics first.")
            return

        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Statistics Report",
            "Statistics_Report.pptx",
            "PowerPoint Files (*.pptx)"
        )

        if not file_path:
            return

        try:
            report = ReportGenerator(
                title="Statistics Analysis Report",
                watermark_text=get_watermark_text(),
                watermark_scope="plot_slides",
            )
            report.add_title_slide(subtitle="Signal Statistical Analysis")
            report.add_bulleted_sections_slide(
                title="Processing Configuration",
                sections=[
                    (
                        "Statistics Parameters",
                        [
                            f"PDF bins: {self.bins_spin.value()}",
                            f"Running window: {self.window_spin.value()} s",
                            f"Signal Conditioning: {self.processing_note}",
                        ],
                    ),
                    (
                        "Distribution Overlays",
                        [
                            f"Normal: {'On' if self.normal_checkbox.isChecked() else 'Off'}",
                            f"Rayleigh: {'On' if self.rayleigh_checkbox.isChecked() else 'Off'}",
                            f"Uniform: {'On' if self.uniform_checkbox.isChecked() else 'Off'}",
                        ],
                    ),
                ],
            )

            # Add PDF plot
            pdf_image = export_plot_to_image(self.pdf_plot)
            report.add_single_plot_slide(pdf_image, "Probability Density Function")

            # Add running stats plot
            stats_image = export_plot_to_image(self.running_stats_plot)
            report.add_single_plot_slide(stats_image, "Running Statistics")

            # Add summary table
            unit = next(iter(self.pdf_data.values())).get("unit", "")
            headers = ["Channel", "RMS"]
            rows = []
            for channel_name, stats_data in self.pdf_data.items():
                rms_value = stats_data.get("overall", {}).get("rms")
                if rms_value is None:
                    rms_text = ""
                elif unit:
                    rms_text = f"{rms_value:.4f} {unit}"
                else:
                    rms_text = f"{rms_value:.4f}"
                rows.append([channel_name, rms_text])
            report.add_rms_table_slide("RMS Summary", headers, rows)

            saved_path = report.save(file_path)
            show_information(self, "Report Generated",
                           f"Report saved to:\n{saved_path}")

        except Exception as e:
            show_critical(self, "Report Error",
                        f"Failed to generate report: {str(e)}")


def create_statistics_window(
    channels_data,
    sample_rate,
    parent=None,
    processing_note: str = "",
    processing_flags: Optional[Dict[str, object]] = None,
):
    """
    Factory function to create a StatisticsWindow.

    This function provides a clean interface for creating statistics windows
    from other parts of the application (e.g., PSD, SPL, SRS tools).

    Parameters
    ----------
    channels_data : list
        List of (name, signal, unit, flight_name) tuples.
    sample_rate : float
        Sample rate in Hz.
    parent : QWidget, optional
        Parent widget.

    Returns
    -------
    StatisticsWindow
        The created statistics window.
    """
    return StatisticsWindow(
        channels_data,
        sample_rate,
        parent,
        processing_note=processing_note,
        processing_flags=processing_flags,
    )
