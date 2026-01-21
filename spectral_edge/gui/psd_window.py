"""
PSD Analysis GUI window for SpectralEdge.

This module provides the graphical user interface for Power Spectral Density
analysis, including file loading, parameter configuration, calculation, and
interactive plotting.

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QGridLayout, QMessageBox, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from pathlib import Path

# Import our custom modules
from spectral_edge.utils.data_loader import load_csv_data, DataLoadError
from spectral_edge.core.psd import (
    calculate_psd_welch, psd_to_db, calculate_rms_from_psd, get_window_options
)


class PSDAnalysisWindow(QMainWindow):
    """
    Main window for PSD Analysis tool.
    
    This window provides a complete interface for:
    - Loading CSV data files
    - Configuring PSD calculation parameters
    - Computing and displaying PSD results
    - Interactive plotting with zoom and pan
    - Multi-channel selection and display
    """
    
    def __init__(self):
        """Initialize the PSD Analysis window."""
        super().__init__()
        
        # Window properties
        self.setWindowTitle("SpectralEdge - PSD Analysis")
        self.setMinimumSize(1400, 900)
        
        # Data storage
        self.time_data = None
        self.signal_data = None
        self.channel_names = None
        self.channel_units = []  # Store units for each channel
        self.sample_rate = None
        self.current_file = None
        
        # PSD results storage (dictionary keyed by channel name)
        self.frequencies = None
        self.psd_results = {}
        self.rms_values = {}
        
        # Channel selection checkboxes
        self.channel_checkboxes = []
        
        # Apply styling
        self._apply_styling()
        
        # Create UI
        self._create_ui()
    
    def _apply_styling(self):
        """Apply aerospace-inspired styling to the window."""
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
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
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
        """)
    
    def _create_ui(self):
        """Create the user interface layout."""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel: Controls
        left_panel = self._create_control_panel()
        main_layout.addWidget(left_panel, stretch=1)
        
        # Right panel: Plot
        right_panel = self._create_plot_panel()
        main_layout.addWidget(right_panel, stretch=3)
    
    def _create_control_panel(self):
        """Create the left control panel with file loading and parameters."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Title
        title = QLabel("PSD Analysis")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #60a5fa;")
        layout.addWidget(title)
        
        # File loading group
        file_group = self._create_file_group()
        layout.addWidget(file_group)
        
        # Channel selection group
        self.channel_group = self._create_channel_group()
        layout.addWidget(self.channel_group)
        
        # Frequency range group
        freq_range_group = self._create_frequency_range_group()
        layout.addWidget(freq_range_group)
        
        # Parameter configuration group
        param_group = self._create_parameter_group()
        layout.addWidget(param_group)
        
        # Calculate button
        self.calc_button = QPushButton("Calculate PSD")
        self.calc_button.setEnabled(False)
        self.calc_button.clicked.connect(self._calculate_psd)
        self.calc_button.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
            }
        """)
        layout.addWidget(self.calc_button)
        
        layout.addStretch()
        
        return panel
    
    def _create_file_group(self):
        """Create the file loading group box."""
        group = QGroupBox("Data File")
        layout = QVBoxLayout()
        
        # File path display
        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        layout.addWidget(self.file_label)
        
        # Load file button
        load_button = QPushButton("Load CSV File")
        load_button.clicked.connect(self._load_file)
        layout.addWidget(load_button)
        
        # File info labels
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #9ca3af; font-size: 10px;")
        layout.addWidget(self.info_label)
        
        group.setLayout(layout)
        return group
    
    def _create_channel_group(self):
        """Create the channel selection group box."""
        group = QGroupBox("Channel Selection")
        layout = QVBoxLayout()
        
        # Scroll area for channel checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.channel_widget = QWidget()
        self.channel_layout = QVBoxLayout(self.channel_widget)
        self.channel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.channel_widget)
        layout.addWidget(scroll)
        
        group.setLayout(layout)
        group.setVisible(False)  # Hidden until data is loaded
        return group
    
    def _create_frequency_range_group(self):
        """Create the frequency range input group box."""
        group = QGroupBox("Frequency Range")
        layout = QGridLayout()
        
        # Min frequency
        layout.addWidget(QLabel("Min Freq (Hz):"), 0, 0)
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0.1, 10000)
        self.freq_min_spin.setValue(10.0)
        self.freq_min_spin.setDecimals(1)
        layout.addWidget(self.freq_min_spin, 0, 1)
        
        # Max frequency
        layout.addWidget(QLabel("Max Freq (Hz):"), 1, 0)
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(1, 100000)
        self.freq_max_spin.setValue(2000.0)
        self.freq_max_spin.setDecimals(1)
        layout.addWidget(self.freq_max_spin, 1, 1)
        
        group.setLayout(layout)
        return group
    
    def _create_parameter_group(self):
        """Create the parameter configuration group box."""
        group = QGroupBox("PSD Parameters")
        layout = QGridLayout()
        
        row = 0
        
        # Window type
        layout.addWidget(QLabel("Window Type:"), row, 0)
        self.window_combo = QComboBox()
        window_options = get_window_options()
        for window_name in window_options.keys():
            self.window_combo.addItem(window_name.capitalize())
        self.window_combo.setCurrentText("Hann")
        layout.addWidget(self.window_combo, row, 1)
        row += 1
        
        # Frequency resolution (df)
        layout.addWidget(QLabel("Δf (Hz):"), row, 0)
        self.df_spin = QDoubleSpinBox()
        self.df_spin.setRange(0.01, 100)
        self.df_spin.setValue(1.0)
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
        self.efficient_fft_checkbox.setChecked(True)
        self.efficient_fft_checkbox.stateChanged.connect(self._update_nperseg_from_df)
        layout.addWidget(self.efficient_fft_checkbox, row, 0, 1, 2)
        row += 1
        
        # Overlap percentage
        layout.addWidget(QLabel("Overlap (%):"), row, 0)
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(50)
        self.overlap_spin.setSingleStep(10)
        layout.addWidget(self.overlap_spin, row, 1)
        row += 1
        
        group.setLayout(layout)
        return group
    
    def _create_plot_panel(self):
        """Create the right plot panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create plot widget using pyqtgraph
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1a1f2e')
        
        # Set labels with proper units
        self.plot_widget.setLabel('left', 'PSD', units='', color='#e0e0e0', size='12pt')
        self.plot_widget.setLabel('bottom', 'Frequency', units='Hz', color='#e0e0e0', size='12pt')
        
        # Enable grid
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Set title
        self.plot_widget.setTitle("Power Spectral Density", color='#60a5fa', size='14pt')
        
        # Enable mouse interaction
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        # Set log-log scale by default
        self.plot_widget.setLogMode(x=True, y=True)
        
        # Set default x-axis range (10-3000 Hz)
        self.plot_widget.setXRange(np.log10(10), np.log10(3000))
        
        # Add legend
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        
        # Configure axis appearance for full box border
        axis_pen = pg.mkPen(color='#4a5568', width=2)
        self.plot_widget.getPlotItem().getAxis('top').setPen(axis_pen)
        self.plot_widget.getPlotItem().getAxis('right').setPen(axis_pen)
        self.plot_widget.getPlotItem().getAxis('top').setStyle(showValues=False)
        self.plot_widget.getPlotItem().getAxis('right').setStyle(showValues=False)
        self.plot_widget.getPlotItem().showAxis('top')
        self.plot_widget.getPlotItem().showAxis('right')
        
        # Format axis tick labels to avoid scientific notation
        self.plot_widget.getPlotItem().getAxis('bottom').setStyle(autoExpandTextSpace=True)
        self.plot_widget.getPlotItem().getAxis('left').setStyle(autoExpandTextSpace=True)
        
        layout.addWidget(self.plot_widget)
        
        return panel
    
    def _update_nperseg_from_df(self):
        """
        Update nperseg based on desired frequency resolution (df).
        
        The relationship is: df = sample_rate / nperseg
        Therefore: nperseg = sample_rate / df
        
        If "Use efficient FFT size" is checked, round to the nearest power of 2.
        """
        if self.sample_rate is None:
            return
        
        df = self.df_spin.value()
        nperseg = int(self.sample_rate / df)
        
        if self.efficient_fft_checkbox.isChecked():
            # Round to nearest power of 2 (preferring larger for better resolution)
            nperseg = 2 ** int(np.ceil(np.log2(nperseg)))
        
        # Update label
        actual_df = self.sample_rate / nperseg
        self.nperseg_label.setText(f"{nperseg} (Δf={actual_df:.3f} Hz)")
    
    def _load_file(self):
        """Handle file loading button click."""
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV Data File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Load the data
            self.time_data, self.signal_data, self.channel_names, self.sample_rate = \
                load_csv_data(file_path)
            
            self.current_file = Path(file_path).name
            
            # Extract units from channel names (e.g., "Accelerometer_X (g)" -> "g")
            self.channel_units = []
            for name in self.channel_names:
                if '(' in name and ')' in name:
                    unit = name[name.find('(')+1:name.find(')')]
                    self.channel_units.append(unit)
                else:
                    self.channel_units.append('')
            
            # Update UI
            self.file_label.setText(f"Loaded: {self.current_file}")
            self.file_label.setStyleSheet("color: #10b981;")
            
            # Display file info
            num_channels = len(self.channel_names)
            duration = len(self.time_data) / self.sample_rate
            info_text = (f"Channels: {num_channels}\n"
                        f"Sample Rate: {self.sample_rate:.1f} Hz\n"
                        f"Duration: {duration:.2f} s\n"
                        f"Samples: {len(self.time_data)}")
            self.info_label.setText(info_text)
            
            # Update nperseg calculation
            self._update_nperseg_from_df()
            
            # Create channel selection checkboxes
            self._create_channel_checkboxes()
            
            # Enable calculate button
            self.calc_button.setEnabled(True)
            
            # Clear previous results
            self.frequencies = None
            self.psd_results = {}
            self.rms_values = {}
            
        except (DataLoadError, FileNotFoundError) as e:
            QMessageBox.critical(self, "Error Loading File", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An error occurred: {e}")
    
    def _create_channel_checkboxes(self):
        """Create checkboxes for channel selection."""
        # Clear existing checkboxes
        for checkbox in self.channel_checkboxes:
            checkbox.deleteLater()
        self.channel_checkboxes.clear()
        
        # Create new checkboxes
        for i, channel_name in enumerate(self.channel_names):
            checkbox = QCheckBox(channel_name)
            checkbox.setChecked(True)  # All channels selected by default
            checkbox.stateChanged.connect(self._update_plot)
            self.channel_layout.addWidget(checkbox)
            self.channel_checkboxes.append(checkbox)
        
        # Show the channel group
        self.channel_group.setVisible(True)
    
    def _calculate_psd(self):
        """Calculate PSD with current parameters for all selected channels."""
        if self.signal_data is None:
            return
        
        try:
            # Get parameters from UI
            window = self.window_combo.currentText().lower()
            df = self.df_spin.value()
            nperseg = int(self.sample_rate / df)
            
            if self.efficient_fft_checkbox.isChecked():
                nperseg = 2 ** int(np.ceil(np.log2(nperseg)))
            
            overlap_percent = self.overlap_spin.value()
            noverlap = int(nperseg * overlap_percent / 100)
            
            # Get frequency range
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()
            
            # Calculate PSD for each channel
            num_channels = self.signal_data.shape[0]
            
            self.psd_results = {}
            self.rms_values = {}
            
            for channel_idx in range(num_channels):
                channel_name = self.channel_names[channel_idx]
                signal = self.signal_data[channel_idx, :]
                
                # Calculate PSD
                frequencies, psd = calculate_psd_welch(
                    signal,
                    self.sample_rate,
                    window=window,
                    nperseg=nperseg,
                    noverlap=noverlap
                )
                
                # Store full frequency range
                if self.frequencies is None:
                    self.frequencies = frequencies
                
                # Calculate RMS over specified frequency range
                rms = calculate_rms_from_psd(frequencies, psd, freq_range=(freq_min, freq_max))
                
                self.psd_results[channel_name] = psd
                self.rms_values[channel_name] = rms
            
            # Update plot
            self._update_plot()
            
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Failed to calculate PSD: {e}")
    
    def _update_plot(self):
        """Update the PSD plot with selected channels."""
        if self.frequencies is None or not self.psd_results:
            return
        
        # Clear previous plot
        self.plot_widget.clear()
        self.legend.clear()
        
        # Re-add legend after clearing
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        
        # Get frequency range for plotting
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Filter frequencies
        freq_mask = (self.frequencies >= freq_min) & (self.frequencies <= freq_max)
        frequencies_plot = self.frequencies[freq_mask]
        
        # Define colors for different channels
        colors = ['#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
        # Plot each selected channel
        plot_count = 0
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                channel_name = self.channel_names[i]
                psd = self.psd_results[channel_name][freq_mask]
                rms = self.rms_values[channel_name]
                unit = self.channel_units[i] if i < len(self.channel_units) else ''
                
                # Create legend label with RMS
                if unit:
                    legend_label = f"{channel_name}: RMS={rms:.4f} {unit}"
                else:
                    legend_label = f"{channel_name}: RMS={rms:.4f}"
                
                # Plot the PSD
                color = colors[plot_count % len(colors)]
                pen = pg.mkPen(color=color, width=2)
                self.plot_widget.plot(
                    frequencies_plot, 
                    psd, 
                    pen=pen,
                    name=legend_label
                )
                
                plot_count += 1
        
        # Update Y-axis label with units
        if self.channel_units and self.channel_units[0]:
            unit = self.channel_units[0]
            self.plot_widget.setLabel('left', f'PSD ({unit}²/Hz)', color='#e0e0e0', size='12pt')
        else:
            self.plot_widget.setLabel('left', 'PSD (units²/Hz)', color='#e0e0e0', size='12pt')
        
        # Set X-axis range to user-specified range
        self.plot_widget.setXRange(np.log10(freq_min), np.log10(freq_max))
