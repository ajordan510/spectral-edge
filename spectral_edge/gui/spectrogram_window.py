"""
Spectrogram GUI window for SpectralEdge.

This module provides a window for displaying spectrograms (time-frequency
representations) of signal data.

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from scipy import signal as scipy_signal
import matplotlib.pyplot as plt
import matplotlib.cm as cm


class LogAxisItem(pg.AxisItem):
    """
    Custom axis item for logarithmic scale with Hz labels.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def tickStrings(self, values, scale, spacing):
        """Override tick string generation to show only Hz values."""
        strings = []
        for v in values:
            actual_value = 10 ** v
            if abs(actual_value - round(actual_value)) < 0.01:
                strings.append(f"{int(round(actual_value))}")
            else:
                strings.append(f"{actual_value:.1f}")
        return strings


class SpectrogramWindow(QMainWindow):
    """
    Window for displaying spectrogram of signal data.
    
    A spectrogram shows how the frequency content of a signal varies over time.
    It's a 2D plot with time on the X-axis, frequency on the Y-axis, and
    color representing the power/amplitude at each time-frequency point.
    """
    
    def __init__(self, time_data, signal_data, channel_name, sample_rate, unit=''):
        """
        Initialize the spectrogram window.
        
        Args:
            time_data: Time array
            signal_data: Signal array (1D)
            channel_name: Name of the channel
            sample_rate: Sampling rate in Hz
            unit: Unit of measurement (e.g., 'g')
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
        self._create_ui()
        
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
        """)
    
    def _create_ui(self):
        """Create the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel: Controls
        left_panel = self._create_control_panel()
        main_layout.addWidget(left_panel, stretch=1)
        
        # Right panel: Spectrogram plot
        right_panel = self._create_plot_panel()
        main_layout.addWidget(right_panel, stretch=4)
    
    def _create_control_panel(self):
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
        
        # Parameters group
        param_group = self._create_parameter_group()
        layout.addWidget(param_group)
        
        # Frequency axis group
        freq_axis_group = self._create_freq_axis_group()
        layout.addWidget(freq_axis_group)
        
        # Colormap group
        colormap_group = self._create_colormap_group()
        layout.addWidget(colormap_group)
        
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
    
    def _create_parameter_group(self):
        """Create parameter configuration group."""
        group = QGroupBox("Parameters")
        layout = QGridLayout()
        
        # Window size (nperseg)
        layout.addWidget(QLabel("Window Size:"), 0, 0)
        self.nperseg_spin = QSpinBox()
        self.nperseg_spin.setRange(64, 8192)
        self.nperseg_spin.setValue(256)
        self.nperseg_spin.setSingleStep(64)
        layout.addWidget(self.nperseg_spin, 0, 1)
        
        # Overlap
        layout.addWidget(QLabel("Overlap (%):"), 1, 0)
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(75)
        self.overlap_spin.setSingleStep(5)
        layout.addWidget(self.overlap_spin, 1, 1)
        
        # SNR threshold
        layout.addWidget(QLabel("SNR Min (dB):"), 2, 0)
        self.snr_spin = QDoubleSpinBox()
        self.snr_spin.setRange(-100, 100)
        self.snr_spin.setValue(-80)
        self.snr_spin.setSingleStep(10)
        layout.addWidget(self.snr_spin, 2, 1)
        
        group.setLayout(layout)
        return group
    
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
        
        layout.addWidget(self.plot_widget)
        
        return panel
    
    def _calculate_spectrogram(self):
        """Calculate and display the spectrogram."""
        try:
            # Get parameters
            nperseg = self.nperseg_spin.value()
            overlap_percent = self.overlap_spin.value()
            noverlap = int(nperseg * overlap_percent / 100)
            snr_min = self.snr_spin.value()
            
            # Calculate spectrogram using scipy
            self.spec_freqs, self.spec_times, Sxx = scipy_signal.spectrogram(
                self.signal_data,
                fs=self.sample_rate,
                window='hann',
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
            freq_min = max(self.spec_freqs[1], 1.0)  # Avoid 0 Hz
            freq_max = self.spec_freqs[-1]
            
            # Create log-spaced frequency array
            num_freq_bins = len(self.spec_freqs)
            log_freqs = np.logspace(np.log10(freq_min), np.log10(freq_max), num_freq_bins)
            
            # Interpolate spectrogram to log frequencies
            spec_interp = np.zeros((len(log_freqs), len(self.spec_times)))
            for i, t_idx in enumerate(range(len(self.spec_times))):
                spec_interp[:, i] = np.interp(log_freqs, self.spec_freqs, self.spec_power[:, i])
            
            # Set image with log frequency axis
            self.img_item.setImage(spec_interp.T, autoLevels=False)
            self.img_item.setLookupTable(lut)
            
            # Set proper scaling
            time_scale = self.spec_times[-1] / spec_interp.shape[1]
            freq_scale = (np.log10(freq_max) - np.log10(freq_min)) / spec_interp.shape[0]
            
            self.img_item.setRect(pg.QtCore.QRectF(
                0, np.log10(freq_min),
                self.spec_times[-1], np.log10(freq_max) - np.log10(freq_min)
            ))
            
            # Set log mode for Y-axis
            self.plot_widget.setLogMode(x=False, y=True)
            
        else:
            # Linear frequency axis
            self.img_item.setImage(self.spec_power.T, autoLevels=False)
            self.img_item.setLookupTable(lut)
            
            # Set proper scaling
            time_scale = self.spec_times[-1] / self.spec_power.shape[1]
            freq_scale = self.spec_freqs[-1] / self.spec_power.shape[0]
            
            self.img_item.setRect(pg.QtCore.QRectF(
                0, 0,
                self.spec_times[-1], self.spec_freqs[-1]
            ))
            
            # Set linear mode
            self.plot_widget.setLogMode(x=False, y=False)
        
        # Update colorbar range
        vmin = np.min(self.spec_power)
        vmax = np.max(self.spec_power)
        self.img_item.setLevels([vmin, vmax])
        
        # Update colorbar
        self.colorbar.setLevels((vmin, vmax))
