"""
Spectrogram GUI window for SpectralEdge.

This module provides a window for displaying spectrograms (time-frequency
representations) of signal data.

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QRadioButton, QButtonGroup, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from scipy import signal as scipy_signal
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from spectral_edge.core.psd import get_window_options


class LogAxisItem(pg.AxisItem):
    """
    Custom axis item for logarithmic scale with Hz labels.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def tickStrings(self, values, scale, spacing):
        """Override tick string generation to show only Hz values at powers of 10."""
        strings = []
        for v in values:
            actual_value = 10 ** v
            
            # Only show values that are close to powers of 10
            log_value = np.log10(actual_value)
            if abs(log_value - round(log_value)) < 0.1:
                strings.append(f"{int(round(actual_value))}")
            else:
                strings.append("")
        
        return strings


class SpectrogramWindow(QMainWindow):
    """
    Window for displaying spectrogram of signal data.
    
    A spectrogram shows how the frequency content of a signal varies over time.
    It's a 2D plot with time on the X-axis, frequency on the Y-axis, and
    color representing the power/amplitude at each time-frequency point.
    """
    
    def __init__(self, time_data, signal_data, channel_name, sample_rate, unit='',
                 window_type='hann', df=1.0, overlap_percent=50, efficient_fft=True,
                 freq_min=10.0, freq_max=2000.0):
        """
        Initialize the spectrogram window.
        
        Args:
            time_data: Time array
            signal_data: Signal array (1D)
            channel_name: Name of the channel
            sample_rate: Sampling rate in Hz
            unit: Unit of measurement (e.g., 'g')
            window_type: Window function type
            df: Frequency resolution in Hz
            overlap_percent: Overlap percentage
            efficient_fft: Use efficient FFT size (power of 2)
            freq_min: Minimum frequency for display
            freq_max: Maximum frequency for display
        """
        super().__init__()
        
        # Store data
        self.time_data = time_data
        self.signal_data = signal_data
        self.channel_name = channel_name
        self.sample_rate = sample_rate
        self.unit = unit
        
        # Spectrogram data
        self.spec_times = None
        self.spec_freqs = None
        self.spec_power = None
        
        # Window properties
        self.setWindowTitle(f"SpectralEdge - Spectrogram: {channel_name}")
        self.setMinimumSize(1200, 800)
        
        # Apply styling
        self._apply_styling()
        
        # Create UI
        self._create_ui(window_type, df, overlap_percent, efficient_fft, freq_min, freq_max)
        
        # Calculate initial spectrogram
        self._calculate_spectrogram()
    
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
        """)
    
    def _create_ui(self, window_type, df, overlap_percent, efficient_fft, freq_min, freq_max):
        """Create the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel: Controls
        left_panel = self._create_control_panel(window_type, df, overlap_percent, efficient_fft, freq_min, freq_max)
        main_layout.addWidget(left_panel, stretch=1)
        
        # Right panel: Spectrogram plot
        right_panel = self._create_plot_panel()
        main_layout.addWidget(right_panel, stretch=4)
    
    def _create_control_panel(self, window_type, df, overlap_percent, efficient_fft, freq_min, freq_max):
        """Create the control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Title
        title = QLabel("Spectrogram")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #60a5fa;")
        layout.addWidget(title)
        
        # Channel info
        info_label = QLabel(f"Channel: {self.channel_name}")
        info_label.setStyleSheet("color: #9ca3af;")
        layout.addWidget(info_label)
        
        # Frequency range group
        freq_range_group = self._create_frequency_range_group(freq_min, freq_max)
        layout.addWidget(freq_range_group)
        
        # Parameters group
        param_group = self._create_parameter_group(window_type, df, overlap_percent, efficient_fft)
        layout.addWidget(param_group)
        
        # Frequency axis group
        freq_axis_group = self._create_freq_axis_group()
        layout.addWidget(freq_axis_group)
        
        # Colormap group
        colormap_group = self._create_colormap_group()
        layout.addWidget(colormap_group)
        
        # Display options group
        display_group = self._create_display_options_group()
        layout.addWidget(display_group)
        
        # Recalculate button
        calc_button = QPushButton("Recalculate Spectrogram")
        calc_button.clicked.connect(self._calculate_spectrogram)
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
        
        layout.addStretch()
        
        return panel
    
    def _create_frequency_range_group(self, freq_min, freq_max):
        """Create frequency range input group box."""
        group = QGroupBox("Frequency Range")
        layout = QGridLayout()
        
        # Min frequency
        layout.addWidget(QLabel("Min Freq (Hz):"), 0, 0)
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0.1, 10000)
        self.freq_min_spin.setValue(freq_min)
        self.freq_min_spin.setDecimals(1)
        layout.addWidget(self.freq_min_spin, 0, 1)
        
        # Max frequency
        layout.addWidget(QLabel("Max Freq (Hz):"), 1, 0)
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(1, 100000)
        self.freq_max_spin.setValue(freq_max)
        self.freq_max_spin.setDecimals(1)
        layout.addWidget(self.freq_max_spin, 1, 1)
        
        group.setLayout(layout)
        return group
    
    def _create_parameter_group(self, window_type, df, overlap_percent, efficient_fft):
        """Create parameter configuration group."""
        group = QGroupBox("Parameters")
        layout = QGridLayout()
        
        row = 0
        
        # Window type
        layout.addWidget(QLabel("Window Type:"), row, 0)
        self.window_combo = QComboBox()
        window_options = get_window_options()
        for window_name in window_options.keys():
            self.window_combo.addItem(window_name.capitalize())
        self.window_combo.setCurrentText(window_type.capitalize())
        self.window_combo.currentTextChanged.connect(self._update_nperseg_from_df)
        layout.addWidget(self.window_combo, row, 1)
        row += 1
        
        # Frequency resolution (df)
        layout.addWidget(QLabel("Δf (Hz):"), row, 0)
        self.df_spin = QDoubleSpinBox()
        self.df_spin.setRange(0.01, 100)
        self.df_spin.setValue(df)
        self.df_spin.setDecimals(2)
        self.df_spin.setSingleStep(0.1)
        self.df_spin.valueChanged.connect(self._update_nperseg_from_df)
        layout.addWidget(self.df_spin, row, 1)
        row += 1
        
        # Segment length (nperseg) - calculated from df
        layout.addWidget(QLabel("Segment Length:"), row, 0)
        self.nperseg_label = QLabel("256")
        self.nperseg_label.setStyleSheet("color: #9ca3af;")
        layout.addWidget(self.nperseg_label, row, 1)
        row += 1
        
        # Use efficient FFT size checkbox
        self.efficient_fft_checkbox = QCheckBox("Use efficient FFT size")
        self.efficient_fft_checkbox.setChecked(efficient_fft)
        self.efficient_fft_checkbox.stateChanged.connect(self._update_nperseg_from_df)
        layout.addWidget(self.efficient_fft_checkbox, row, 0, 1, 2)
        row += 1
        
        # Overlap
        layout.addWidget(QLabel("Overlap (%):"), row, 0)
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(overlap_percent)
        self.overlap_spin.setSingleStep(5)
        layout.addWidget(self.overlap_spin, row, 1)
        row += 1
        
        # SNR threshold
        layout.addWidget(QLabel("SNR Min (dB):"), row, 0)
        self.snr_spin = QDoubleSpinBox()
        self.snr_spin.setRange(-100, 100)
        self.snr_spin.setValue(-80)
        self.snr_spin.setSingleStep(10)
        layout.addWidget(self.snr_spin, row, 1)
        row += 1
        
        group.setLayout(layout)
        
        # Initial nperseg calculation
        self._update_nperseg_from_df()
        
        return group
    
    def _update_nperseg_from_df(self):
        """Update nperseg based on desired frequency resolution (df)."""
        df = self.df_spin.value()
        nperseg = int(self.sample_rate / df)
        
        if self.efficient_fft_checkbox.isChecked():
            nperseg = 2 ** int(np.ceil(np.log2(nperseg)))
        
        # Update label
        actual_df = self.sample_rate / nperseg
        self.nperseg_label.setText(f"{nperseg} (Δf={actual_df:.3f} Hz)")
    
    def _create_freq_axis_group(self):
        """Create frequency axis scaling group."""
        group = QGroupBox("Frequency Axis")
        layout = QVBoxLayout()
        
        # Radio buttons for linear/log
        self.freq_button_group = QButtonGroup()
        
        self.freq_linear_radio = QRadioButton("Linear")
        self.freq_log_radio = QRadioButton("Logarithmic")
        self.freq_log_radio.setChecked(True)
        
        self.freq_button_group.addButton(self.freq_linear_radio)
        self.freq_button_group.addButton(self.freq_log_radio)
        
        layout.addWidget(self.freq_linear_radio)
        layout.addWidget(self.freq_log_radio)
        
        group.setLayout(layout)
        return group
    
    def _create_colormap_group(self):
        """Create colormap selection group."""
        group = QGroupBox("Colormap")
        layout = QVBoxLayout()
        
        self.colormap_combo = QComboBox()
        colormaps = ['viridis', 'plasma', 'inferno', 'magma', 'jet', 'hot', 'cool', 'turbo']
        for cmap in colormaps:
            self.colormap_combo.addItem(cmap.capitalize())
        layout.addWidget(self.colormap_combo)
        
        group.setLayout(layout)
        return group
    
    def _create_display_options_group(self):
        """Create display options group."""
        group = QGroupBox("Display Options")
        layout = QVBoxLayout()
        
        # Show crosshair checkbox
        self.show_crosshair_checkbox = QCheckBox("Show Crosshair")
        self.show_crosshair_checkbox.setChecked(False)
        layout.addWidget(self.show_crosshair_checkbox)
        
        group.setLayout(layout)
        return group
    
    def _create_plot_panel(self):
        """Create the plot panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create image widget for spectrogram
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1a1f2e')
        
        # Set labels
        self.plot_widget.setLabel('bottom', 'Time', units='s', color='#e0e0e0', size='12pt')
        self.plot_widget.setLabel('left', 'Frequency (Hz)', color='#e0e0e0', size='12pt')
        
        # Set title
        title_text = f"Spectrogram: {self.channel_name}"
        self.plot_widget.setTitle(title_text, color='#60a5fa', size='14pt')
        
        # Create image item for spectrogram
        self.img_item = pg.ImageItem()
        self.plot_widget.addItem(self.img_item)
        
        # Add colorbar
        self.colorbar = pg.ColorBarItem(
            values=(0, 1),
            colorMap='viridis',
            label='Power (dB)'
        )
        self.colorbar.setImageItem(self.img_item)
        
        # Add crosshair for cursor position display
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#60a5fa', width=1, style=Qt.PenStyle.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#60a5fa', width=1, style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        
        # Add label for cursor coordinates
        self.coord_label = pg.TextItem(anchor=(0, 1), color='#e0e0e0')
        self.plot_widget.addItem(self.coord_label, ignoreBounds=True)
        
        # Disable auto-range to prevent crosshair from panning
        self.plot_widget.getPlotItem().vb.disableAutoRange()
        
        # Connect mouse move event
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
        # Hide crosshair initially
        self.vLine.setVisible(False)
        self.hLine.setVisible(False)
        self.coord_label.setVisible(False)
        
        layout.addWidget(self.plot_widget)
        
        return panel
    
    def _on_mouse_moved(self, pos):
        """Handle mouse movement over the plot to show cursor coordinates."""
        # Only show if checkbox is checked
        if not self.show_crosshair_checkbox.isChecked():
            self.vLine.setVisible(False)
            self.hLine.setVisible(False)
            self.coord_label.setVisible(False)
            return
        
        # Check if mouse is within plot area
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            
            # Get time and frequency values
            time_val = mouse_point.x()
            
            # Check if frequency axis is log or linear
            if self.freq_log_radio.isChecked():
                freq_val = 10 ** mouse_point.y()
            else:
                freq_val = mouse_point.y()
            
            # Update crosshair position
            self.vLine.setPos(mouse_point.x())
            self.hLine.setPos(mouse_point.y())
            self.vLine.setVisible(True)
            self.hLine.setVisible(True)
            
            # Update coordinate label
            label_text = f"t = {time_val:.3f} s\nf = {freq_val:.2f} Hz"
            
            self.coord_label.setText(label_text)
            self.coord_label.setPos(mouse_point.x(), mouse_point.y())
            self.coord_label.setVisible(True)
        else:
            # Hide crosshair when mouse leaves plot area
            self.vLine.setVisible(False)
            self.hLine.setVisible(False)
            self.coord_label.setVisible(False)
    
    def _calculate_spectrogram(self):
        """Calculate and display the spectrogram."""
        try:
            # Get parameters
            window = self.window_combo.currentText().lower()
            df = self.df_spin.value()
            nperseg = int(self.sample_rate / df)
            
            if self.efficient_fft_checkbox.isChecked():
                nperseg = 2 ** int(np.ceil(np.log2(nperseg)))
            
            overlap_percent = self.overlap_spin.value()
            noverlap = int(nperseg * overlap_percent / 100)
            snr_min = self.snr_spin.value()
            
            # Calculate spectrogram using scipy
            self.spec_freqs, self.spec_times, Sxx = scipy_signal.spectrogram(
                self.signal_data,
                fs=self.sample_rate,
                window=window,
                nperseg=nperseg,
                noverlap=noverlap,
                scaling='density'
            )
            
            # Convert to dB
            # Add small epsilon to avoid log(0)
            epsilon = 1e-20
            Sxx_db = 10 * np.log10(Sxx + epsilon)
            
            # Apply SNR threshold
            Sxx_db[Sxx_db < snr_min] = snr_min
            
            self.spec_power = Sxx_db
            
            # Update plot
            self._update_plot()
            
        except Exception as e:
            print(f"Error calculating spectrogram: {e}")
    
    def _update_plot(self):
        """Update the spectrogram plot."""
        if self.spec_power is None:
            return
        
        # Get frequency range
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Filter frequencies
        freq_mask = (self.spec_freqs >= freq_min) & (self.spec_freqs <= freq_max)
        if not np.any(freq_mask):
            return
        
        spec_freqs_filtered = self.spec_freqs[freq_mask]
        spec_power_filtered = self.spec_power[freq_mask, :]
        
        # Get colormap
        cmap_name = self.colormap_combo.currentText().lower()
        cmap = cm.get_cmap(cmap_name)
        
        # Convert matplotlib colormap to pyqtgraph colormap
        lut = (cmap(np.linspace(0, 1, 256)) * 255).astype(np.uint8)
        
        # Check if frequency axis should be log
        use_log_freq = self.freq_log_radio.isChecked()
        
        if use_log_freq:
            # For log frequency axis, we need to resample the spectrogram
            # to logarithmic frequency spacing
            freq_min_plot = max(spec_freqs_filtered[0], 1.0)  # Avoid 0 Hz
            freq_max_plot = spec_freqs_filtered[-1]
            
            # Create log-spaced frequency array
            num_freq_bins = len(spec_freqs_filtered)
            log_freqs = np.logspace(np.log10(freq_min_plot), np.log10(freq_max_plot), num_freq_bins)
            
            # Interpolate spectrogram to log frequencies
            spec_interp = np.zeros((len(log_freqs), len(self.spec_times)))
            for i, t_idx in enumerate(range(len(self.spec_times))):
                spec_interp[:, i] = np.interp(log_freqs, spec_freqs_filtered, spec_power_filtered[:, i])
            
            # Set image with log frequency axis
            self.img_item.setImage(spec_interp.T, autoLevels=False)
            self.img_item.setLookupTable(lut)
            
            # Set proper scaling
            self.img_item.setRect(pg.QtCore.QRectF(
                0, np.log10(freq_min_plot),
                self.spec_times[-1], np.log10(freq_max_plot) - np.log10(freq_min_plot)
            ))
            
            # Set log mode for Y-axis
            self.plot_widget.setLogMode(x=False, y=True)
            
            # Set custom frequency ticks (powers of 10 only)
            self._set_frequency_ticks_log(freq_min_plot, freq_max_plot)
            self.plot_widget.setLabel('left', 'Frequency (Hz)', color='#e0e0e0', size='12pt')
            
        else:
            # Linear frequency axis
            self.img_item.setImage(spec_power_filtered.T, autoLevels=False)
            self.img_item.setLookupTable(lut)
            
            # Set proper scaling
            self.img_item.setRect(pg.QtCore.QRectF(
                0, spec_freqs_filtered[0],
                self.spec_times[-1], spec_freqs_filtered[-1] - spec_freqs_filtered[0]
            ))
            
            # Set linear mode
            self.plot_widget.setLogMode(x=False, y=False)
            
            # Reset to standard axis
            standard_axis = pg.AxisItem(orientation='left')
            self.plot_widget.setAxisItems({'left': standard_axis})
            self.plot_widget.setLabel('left', 'Frequency (Hz)', color='#e0e0e0', size='12pt')
        
        # Update colorbar range
        vmin = np.min(spec_power_filtered)
        vmax = np.max(spec_power_filtered)
        self.img_item.setLevels([vmin, vmax])
        
        # Update colorbar
        self.colorbar.setLevels((vmin, vmax))
        
        # Re-enable auto-range for user interaction, but keep current view
        self.plot_widget.getPlotItem().vb.enableAutoRange(enable=False)
    
    def _set_frequency_ticks_log(self, freq_min, freq_max):
        """Set frequency axis ticks to only show powers of 10 in log scale."""
        # Generate powers of 10 within the frequency range
        min_power = int(np.floor(np.log10(freq_min)))
        max_power = int(np.ceil(np.log10(freq_max)))
        
        # Create tick values (in log space)
        tick_values = []
        tick_labels = []
        
        for power in range(min_power, max_power + 1):
            freq = 10 ** power
            if freq >= freq_min and freq <= freq_max:
                tick_values.append(np.log10(freq))
                tick_labels.append(str(int(freq)))
        
        # Set the ticks on the left axis
        left_axis = self.plot_widget.getPlotItem().getAxis('left')
        left_axis.setTicks([[(val, label) for val, label in zip(tick_values, tick_labels)]])
