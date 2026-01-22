"""
Spectrogram GUI window for SpectralEdge.

This module provides a window for displaying spectrograms (time-frequency
representations) of signal data. Supports up to 4 channels simultaneously.

Features:
- SNR-based color scale control
- Actual df display when efficient FFT is used
- Custom axis limits with auto/manual toggle
- Colorbar visibility toggle
- Parameter and display panel separation
- Vertical carousel navigation

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QRadioButton, QButtonGroup, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from scipy import signal as scipy_signal
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from spectral_edge.core.psd import get_window_options


class ColorBarItem(pg.GraphicsObject):
    """
    Custom colorbar for spectrogram display.
    """
    
    def __init__(self, colormap, vmin, vmax, label="Power (dB)"):
        super().__init__()
        self.colormap = colormap
        self.vmin = vmin
        self.vmax = vmax
        self.label = label
        
    def paint(self, p, *args):
        pass
    
    def boundingRect(self):
        return pg.QtCore.QRectF(0, 0, 1, 1)


class SpectrogramWindow(QMainWindow):
    """
    Window for displaying spectrogram of signal data.
    
    A spectrogram shows how the frequency content of a signal varies over time.
    It's a 2D plot with time on the X-axis, frequency on the Y-axis, and
    color representing the power/amplitude at each time-frequency point.
    
    Supports up to 4 channels displayed simultaneously in adaptive layout.
    """
    
    def __init__(self, time_data, channels_data, sample_rate,
                 window_type='hann', df=1.0, overlap_percent=50, efficient_fft=True,
                 freq_min=10.0, freq_max=2000.0):
        """
        Initialize the spectrogram window.
        
        Args:
            time_data: Time array
            channels_data: List of (channel_name, signal_data, unit) tuples (up to 4)
            sample_rate: Sampling rate in Hz
            window_type: Window function type
            df: Desired frequency resolution in Hz
            overlap_percent: Overlap percentage
            efficient_fft: Use efficient FFT size (power of 2)
            freq_min: Minimum frequency for display
            freq_max: Maximum frequency for display
        """
        super().__init__()
        
        # Store data
        self.time_data = time_data
        self.channels_data = channels_data[:4]  # Limit to 4 channels
        self.n_channels = len(self.channels_data)
        self.sample_rate = sample_rate
        
        # Spectrogram data for each channel
        self.spec_data = []  # List of (times, freqs, power_db) tuples
        
        # Store actual parameters used
        self.actual_df = None
        self.actual_nperseg = None
        
        # Window properties
        if self.n_channels == 1:
            self.setWindowTitle(f"SpectralEdge - Spectrogram: {self.channels_data[0][0]}")
        else:
            channel_names = ", ".join([name for name, _, _ in self.channels_data])
            self.setWindowTitle(f"SpectralEdge - Spectrogram: {channel_names}")
        
        self.setMinimumSize(1400, 900)
        
        # Apply styling
        self._apply_styling()
        
        # Store initial parameters
        self.initial_params = {
            'window_type': window_type,
            'df': df,
            'overlap_percent': overlap_percent,
            'efficient_fft': efficient_fft,
            'freq_min': freq_min,
            'freq_max': freq_max
        }
        
        # Create UI
        self._create_ui(window_type, df, overlap_percent, efficient_fft, freq_min, freq_max)
        
        # Calculate initial spectrograms
        self._calculate_spectrograms()
    
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
                padding: 8px;
                font-size: 13px;
                min-height: 25px;
            }
            QRadioButton {
                color: #e0e0e0;
                padding: 5px;
            }
            QCheckBox {
                color: #e0e0e0;
                padding: 5px;
            }
            QScrollArea {
                border: none;
                background-color: #1a1f2e;
            }
        """)
    
    def _create_ui(self, window_type, df, overlap_percent, efficient_fft, freq_min, freq_max):
        """Create the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - spectrograms (larger)
        spec_panel = self._create_spectrogram_panel()
        main_layout.addWidget(spec_panel, stretch=4)
        
        # Right panel - controls (scrollable)
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # Parameters group
        params_group = self._create_parameters_group(window_type, df, overlap_percent, efficient_fft)
        control_layout.addWidget(params_group)
        
        # Display options group
        display_group = self._create_display_options_group(freq_min, freq_max)
        control_layout.addWidget(display_group)
        
        # Axis limits group
        axis_group = self._create_axis_limits_group()
        control_layout.addWidget(axis_group)
        
        # Recalculate button
        recalc_button = QPushButton("Recalculate")
        recalc_button.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
        """)
        recalc_button.clicked.connect(self._calculate_spectrograms)
        control_layout.addWidget(recalc_button)
        
        control_layout.addStretch()
        
        control_scroll.setWidget(control_widget)
        main_layout.addWidget(control_scroll, stretch=1)
    
    def _create_spectrogram_panel(self):
        """Create the spectrogram display panel with adaptive layout."""
        panel = QWidget()
        
        # Determine layout based on number of channels
        if self.n_channels == 1:
            # Single plot
            layout = QVBoxLayout(panel)
            self.plot_widgets = [self._create_plot_widget(0)]
            self.image_items = [None]
            self.colorbars = [None]
            layout.addWidget(self.plot_widgets[0])
        elif self.n_channels == 2:
            # Vertical stack (2 rows, 1 column)
            layout = QVBoxLayout(panel)
            self.plot_widgets = []
            self.image_items = []
            self.colorbars = []
            for i in range(2):
                widget = self._create_plot_widget(i)
                self.plot_widgets.append(widget)
                self.image_items.append(None)
                self.colorbars.append(None)
                layout.addWidget(widget)
        elif self.n_channels == 3:
            # 2x2 grid with empty bottom-right
            layout = QGridLayout(panel)
            self.plot_widgets = []
            self.image_items = []
            self.colorbars = []
            positions = [(0, 0), (0, 1), (1, 0)]
            for i, (row, col) in enumerate(positions):
                widget = self._create_plot_widget(i)
                self.plot_widgets.append(widget)
                self.image_items.append(None)
                self.colorbars.append(None)
                layout.addWidget(widget, row, col)
        else:  # 4 channels
            # 2x2 grid
            layout = QGridLayout(panel)
            self.plot_widgets = []
            self.image_items = []
            self.colorbars = []
            positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
            for i, (row, col) in enumerate(positions):
                widget = self._create_plot_widget(i)
                self.plot_widgets.append(widget)
                self.image_items.append(None)
                self.colorbars.append(None)
                layout.addWidget(widget, row, col)
        
        return panel
    
    def _create_plot_widget(self, channel_idx):
        """Create a single spectrogram plot widget."""
        channel_name, _, unit = self.channels_data[channel_idx]
        
        # Create plot widget
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('#1a1f2e')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Set labels
        plot_widget.setLabel('bottom', 'Time (s)', color='#e0e0e0', size='11pt')
        plot_widget.setLabel('left', 'Frequency (Hz)', color='#e0e0e0', size='11pt')
        plot_widget.setTitle(f"{channel_name}", color='#e0e0e0', size='12pt')
        
        return plot_widget
    
    def _create_parameters_group(self, window_type, df, overlap_percent, efficient_fft):
        """Create parameters group."""
        group = QGroupBox("Parameters")
        layout = QGridLayout()
        
        row = 0
        
        # Window type
        layout.addWidget(QLabel("Window:"), row, 0)
        self.window_combo = QComboBox()
        window_options = get_window_options()
        for window_name in window_options.keys():
            self.window_combo.addItem(window_name.capitalize())
        self.window_combo.setCurrentText(window_type.capitalize())
        layout.addWidget(self.window_combo, row, 1)
        row += 1
        
        # Desired frequency resolution
        layout.addWidget(QLabel("Desired Δf (Hz):"), row, 0)
        self.df_spin = QDoubleSpinBox()
        self.df_spin.setRange(0.1, 100)
        self.df_spin.setValue(df)
        self.df_spin.setDecimals(1)
        layout.addWidget(self.df_spin, row, 1)
        row += 1
        
        # Actual df display (read-only)
        layout.addWidget(QLabel("Actual Δf (Hz):"), row, 0)
        self.actual_df_label = QLabel("--")
        self.actual_df_label.setStyleSheet("color: #60a5fa; font-weight: bold;")
        layout.addWidget(self.actual_df_label, row, 1)
        row += 1
        
        # Overlap
        layout.addWidget(QLabel("Overlap (%):"), row, 0)
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(overlap_percent)
        layout.addWidget(self.overlap_spin, row, 1)
        row += 1
        
        # Efficient FFT
        self.efficient_fft_checkbox = QCheckBox("Efficient FFT (power of 2)")
        self.efficient_fft_checkbox.setChecked(efficient_fft)
        layout.addWidget(self.efficient_fft_checkbox, row, 0, 1, 2)
        row += 1
        
        group.setLayout(layout)
        return group
    
    def _create_display_options_group(self, freq_min, freq_max):
        """Create display options group."""
        group = QGroupBox("Display Options")
        layout = QGridLayout()
        
        row = 0
        
        # Frequency range
        layout.addWidget(QLabel("Freq Range:"), row, 0, 1, 2)
        row += 1
        
        layout.addWidget(QLabel("Min (Hz):"), row, 0)
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0.1, 100000)
        self.freq_min_spin.setValue(freq_min)
        self.freq_min_spin.setDecimals(1)
        self.freq_min_spin.valueChanged.connect(self._update_plots)
        layout.addWidget(self.freq_min_spin, row, 1)
        row += 1
        
        layout.addWidget(QLabel("Max (Hz):"), row, 0)
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(1, 100000)
        self.freq_max_spin.setValue(freq_max)
        self.freq_max_spin.setDecimals(1)
        self.freq_max_spin.valueChanged.connect(self._update_plots)
        layout.addWidget(self.freq_max_spin, row, 1)
        row += 1
        
        # Frequency scale
        layout.addWidget(QLabel("Y-Scale:"), row, 0)
        scale_layout = QHBoxLayout()
        self.scale_group = QButtonGroup()
        
        self.linear_radio = QRadioButton("Linear")
        self.log_radio = QRadioButton("Log")
        self.log_radio.setChecked(True)
        
        self.scale_group.addButton(self.linear_radio)
        self.scale_group.addButton(self.log_radio)
        
        self.linear_radio.toggled.connect(self._update_plots)
        
        scale_layout.addWidget(self.linear_radio)
        scale_layout.addWidget(self.log_radio)
        layout.addLayout(scale_layout, row, 1)
        row += 1
        
        # Color map
        layout.addWidget(QLabel("Colormap:"), row, 0)
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(['viridis', 'plasma', 'inferno', 'magma', 'jet', 'hot', 'cool'])
        self.colormap_combo.setCurrentText('viridis')
        self.colormap_combo.currentTextChanged.connect(self._update_plots)
        layout.addWidget(self.colormap_combo, row, 1)
        row += 1
        
        # SNR (dB) for color scale
        layout.addWidget(QLabel("SNR (dB):"), row, 0)
        self.snr_spin = QSpinBox()
        self.snr_spin.setRange(10, 100)
        self.snr_spin.setValue(60)
        self.snr_spin.setSingleStep(5)
        self.snr_spin.setToolTip("Signal-to-noise ratio for color scale dynamic range")
        self.snr_spin.valueChanged.connect(self._update_plots)
        layout.addWidget(self.snr_spin, row, 1)
        row += 1
        
        # Show colorbar
        self.show_colorbar_checkbox = QCheckBox("Show Colorbar")
        self.show_colorbar_checkbox.setChecked(True)
        self.show_colorbar_checkbox.toggled.connect(self._update_plots)
        layout.addWidget(self.show_colorbar_checkbox, row, 0, 1, 2)
        row += 1
        
        group.setLayout(layout)
        return group
    
    def _create_axis_limits_group(self):
        """Create axis limits control group."""
        group = QGroupBox("Axis Limits")
        layout = QGridLayout()
        
        row = 0
        
        # Auto/Manual toggle
        self.auto_limits_checkbox = QCheckBox("Auto Limits")
        self.auto_limits_checkbox.setChecked(True)
        self.auto_limits_checkbox.toggled.connect(self._on_auto_limits_toggled)
        layout.addWidget(self.auto_limits_checkbox, row, 0, 1, 2)
        row += 1
        
        # Time limits
        layout.addWidget(QLabel("Time (s):"), row, 0, 1, 2)
        row += 1
        
        layout.addWidget(QLabel("Min:"), row, 0)
        self.time_min_edit = QLineEdit()
        self.time_min_edit.setText("0.0")
        self.time_min_edit.setPlaceholderText("e.g., 0 or 0.0")
        self.time_min_edit.setToolTip("Enter time in seconds (standard or scientific notation)")
        self.time_min_edit.setEnabled(False)
        layout.addWidget(self.time_min_edit, row, 1)
        row += 1
        
        layout.addWidget(QLabel("Max:"), row, 0)
        self.time_max_edit = QLineEdit()
        self.time_max_edit.setText("100.0")
        self.time_max_edit.setPlaceholderText("e.g., 100 or 1e2")
        self.time_max_edit.setToolTip("Enter time in seconds (standard or scientific notation)")
        self.time_max_edit.setEnabled(False)
        layout.addWidget(self.time_max_edit, row, 1)
        row += 1
        
        # Apply limits button
        self.apply_limits_button = QPushButton("Apply Limits")
        self.apply_limits_button.setEnabled(False)
        self.apply_limits_button.clicked.connect(self._apply_custom_limits)
        layout.addWidget(self.apply_limits_button, row, 0, 1, 2)
        row += 1
        
        group.setLayout(layout)
        return group
    
    def _on_auto_limits_toggled(self, checked):
        """Handle auto limits checkbox toggle."""
        # Enable/disable manual limit controls
        self.time_min_edit.setEnabled(not checked)
        self.time_max_edit.setEnabled(not checked)
        self.apply_limits_button.setEnabled(not checked)
        
        if checked:
            # Revert to auto limits
            self._update_plots()
    
    def _apply_custom_limits(self):
        """Apply custom axis limits to all plots."""
        # Parse time limits from text fields
        try:
            time_min = float(self.time_min_edit.text())
            time_max = float(self.time_max_edit.text())
        except ValueError as e:
            from spectral_edge.utils.message_box import show_warning
            show_warning(self, "Invalid Input", 
                        f"Please enter valid numbers (standard or scientific notation).\nError: {e}")
            return
        
        if time_min >= time_max:
            from spectral_edge.utils.message_box import show_warning
            show_warning(self, "Invalid Limits", "Time minimum must be less than maximum.")
            return
        
        # Apply to all plots
        for plot_widget in self.plot_widgets:
            plot_widget.setXRange(time_min, time_max, padding=0)
        
    def _calculate_spectrograms(self):
        """Calculate spectrograms for all channels."""
        # Get parameters
        window_type = self.window_combo.currentText().lower()
        df = self.df_spin.value()
        overlap_percent = self.overlap_spin.value()
        efficient_fft = self.efficient_fft_checkbox.isChecked()
        
        # Calculate nperseg from df
        nperseg = int(self.sample_rate / df)
        
        # Use efficient FFT size if requested
        if efficient_fft:
            nperseg = 2 ** int(np.ceil(np.log2(nperseg)))
        
        # Store actual nperseg
        self.actual_nperseg = nperseg
        
        # Calculate actual df
        self.actual_df = self.sample_rate / nperseg
        
        # Update actual df display
        self.actual_df_label.setText(f"{self.actual_df:.3f}")
        
        # Calculate noverlap
        noverlap = int(nperseg * overlap_percent / 100)
        
        # Clear previous data
        self.spec_data = []
        
        # Calculate spectrogram for each channel
        for i, (channel_name, signal_data, unit) in enumerate(self.channels_data):
            # Calculate spectrogram
            freqs, times, Sxx = scipy_signal.spectrogram(
                signal_data,
                fs=self.sample_rate,
                window=window_type,
                nperseg=nperseg,
                noverlap=noverlap,
                scaling='density'
            )
            
            # Convert to dB
            Sxx_db = 10 * np.log10(Sxx + 1e-20)
            
            # Store
            self.spec_data.append((times, freqs, Sxx_db))
        
        # Update plots
        self._update_plots()
    
    def _update_plots(self):
        """Update all spectrogram plots."""
        if not self.spec_data:
            return
        
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        colormap_name = self.colormap_combo.currentText()
        use_log_scale = self.log_radio.isChecked()
        snr_db = self.snr_spin.value()
        show_colorbar = self.show_colorbar_checkbox.isChecked()
        
        # Get colormap
        cmap = cm.get_cmap(colormap_name)
        
        for i, (times, freqs, Sxx_db) in enumerate(self.spec_data):
            plot_widget = self.plot_widgets[i]
            channel_name, _, unit = self.channels_data[i]
            
            # Clear previous plot
            plot_widget.clear()
            
            # Filter frequency range
            freq_mask = (freqs >= freq_min) & (freqs <= freq_max)
            freqs_plot = freqs[freq_mask]
            Sxx_plot = Sxx_db[freq_mask, :]
            
            if len(freqs_plot) == 0:
                continue
            
            # Calculate color scale based on SNR
            max_power = np.max(Sxx_plot)
            min_power = max_power - snr_db
            
            # Create image item
            img = pg.ImageItem()
            plot_widget.addItem(img)
            
            # Set data with SNR-based levels
            img.setImage(Sxx_plot, autoLevels=False, levels=(min_power, max_power))
            
            # Set position and scale
            if use_log_scale:
                # For log scale, we need to transform frequencies
                log_freqs = np.log10(freqs_plot)
                img.setRect(pg.QtCore.QRectF(
                    times[0],
                    log_freqs[0],
                    times[-1] - times[0],
                    log_freqs[-1] - log_freqs[0]
                ))
                plot_widget.setLabel('left', 'Frequency (Hz, log)', color='#e0e0e0', size='11pt')
            else:
                img.setRect(pg.QtCore.QRectF(
                    times[0],
                    freqs_plot[0],
                    times[-1] - times[0],
                    freqs_plot[-1] - freqs_plot[0]
                ))
                plot_widget.setLabel('left', 'Frequency (Hz)', color='#e0e0e0', size='11pt')
            
            # Apply colormap
            colors = []
            for j in range(256):
                rgba = cmap(j / 255.0)
                colors.append((int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255), 255))
            
            lut = np.array(colors, dtype=np.ubyte)
            img.setLookupTable(lut)
            
            # Store image item
            self.image_items[i] = img
            
            # Add colorbar if requested
            if show_colorbar:
                # Create colorbar using GradientLegend
                colorbar = pg.GradientLegend((20, 150), (-10, -10))
                colorbar.setGradient(img.getHistogram()[1])
                colorbar.setLabels({str(int(min_power)): 0, str(int(max_power)): 1})
                plot_widget.addItem(colorbar)
                self.colorbars[i] = colorbar
            
            # Update title
            if unit:
                plot_widget.setTitle(f"{channel_name} ({unit}) | SNR: {snr_db} dB", 
                                    color='#e0e0e0', size='12pt')
            else:
                plot_widget.setTitle(f"{channel_name} | SNR: {snr_db} dB", 
                                    color='#e0e0e0', size='12pt')
            
            # Set time limits if auto
            if self.auto_limits_checkbox.isChecked():
                plot_widget.setXRange(times[0], times[-1], padding=0.02)
                # Update text fields for reference
                self.time_min_edit.setText(f"{times[0]:.3f}")
                self.time_max_edit.setText(f"{times[-1]:.3f}")
