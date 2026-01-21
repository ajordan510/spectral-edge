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
    QGroupBox, QGridLayout, QMessageBox, QCheckBox
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
    """
    
    def __init__(self):
        """Initialize the PSD Analysis window."""
        super().__init__()
        
        # Window properties
        self.setWindowTitle("SpectralEdge - PSD Analysis")
        self.setMinimumSize(1200, 800)
        
        # Data storage
        self.time_data = None
        self.signal_data = None
        self.channel_names = None
        self.sample_rate = None
        self.current_file = None
        
        # PSD results storage
        self.frequencies = None
        self.psd_results = None
        
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
        
        # Results display
        results_group = self._create_results_group()
        layout.addWidget(results_group)
        
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
        
        # Segment length (nperseg)
        layout.addWidget(QLabel("Segment Length:"), row, 0)
        self.nperseg_spin = QSpinBox()
        self.nperseg_spin.setRange(64, 8192)
        self.nperseg_spin.setValue(256)
        self.nperseg_spin.setSingleStep(64)
        layout.addWidget(self.nperseg_spin, row, 1)
        row += 1
        
        # Overlap percentage
        layout.addWidget(QLabel("Overlap (%):"), row, 0)
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(50)
        self.overlap_spin.setSingleStep(10)
        layout.addWidget(self.overlap_spin, row, 1)
        row += 1
        
        # Display in dB
        self.db_checkbox = QCheckBox("Display in dB")
        self.db_checkbox.setChecked(True)
        self.db_checkbox.stateChanged.connect(self._update_plot)
        layout.addWidget(self.db_checkbox, row, 0, 1, 2)
        row += 1
        
        group.setLayout(layout)
        return group
    
    def _create_results_group(self):
        """Create the results display group box."""
        group = QGroupBox("Results")
        layout = QVBoxLayout()
        
        self.results_label = QLabel("No results yet")
        self.results_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        self.results_label.setWordWrap(True)
        layout.addWidget(self.results_label)
        
        group.setLayout(layout)
        return group
    
    def _create_plot_panel(self):
        """Create the right plot panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create plot widget using pyqtgraph
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1a1f2e')
        self.plot_widget.setLabel('left', 'PSD', color='#e0e0e0', size='12pt')
        self.plot_widget.setLabel('bottom', 'Frequency (Hz)', color='#e0e0e0', size='12pt')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setTitle("Power Spectral Density", color='#60a5fa', size='14pt')
        
        # Enable mouse interaction
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        layout.addWidget(self.plot_widget)
        
        return panel
    
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
            
            # Enable calculate button
            self.calc_button.setEnabled(True)
            
            # Clear previous results
            self.frequencies = None
            self.psd_results = None
            self.results_label.setText("Data loaded. Click 'Calculate PSD' to analyze.")
            
        except (DataLoadError, FileNotFoundError) as e:
            QMessageBox.critical(self, "Error Loading File", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An error occurred: {e}")
    
    def _calculate_psd(self):
        """Calculate PSD with current parameters."""
        if self.signal_data is None:
            return
        
        try:
            # Get parameters from UI
            window = self.window_combo.currentText().lower()
            nperseg = self.nperseg_spin.value()
            overlap_percent = self.overlap_spin.value()
            noverlap = int(nperseg * overlap_percent / 100)
            
            # Calculate PSD for each channel
            num_channels = self.signal_data.shape[0]
            
            # For simplicity, we'll process the first channel
            # (Multi-channel support can be added later)
            channel_idx = 0
            signal = self.signal_data[channel_idx, :]
            
            # Calculate PSD
            self.frequencies, psd = calculate_psd_welch(
                signal,
                self.sample_rate,
                window=window,
                nperseg=nperseg,
                noverlap=noverlap
            )
            
            self.psd_results = psd
            
            # Calculate RMS
            rms = calculate_rms_from_psd(self.frequencies, psd)
            
            # Update results display
            results_text = (f"Channel: {self.channel_names[channel_idx]}\n"
                           f"RMS: {rms:.4f}\n"
                           f"Frequency Range: {self.frequencies[0]:.1f} - "
                           f"{self.frequencies[-1]:.1f} Hz")
            self.results_label.setText(results_text)
            self.results_label.setStyleSheet("color: #10b981; font-size: 11px;")
            
            # Update plot
            self._update_plot()
            
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Failed to calculate PSD: {e}")
    
    def _update_plot(self):
        """Update the PSD plot with current results."""
        if self.frequencies is None or self.psd_results is None:
            return
        
        # Clear previous plot
        self.plot_widget.clear()
        
        # Determine if we should display in dB
        use_db = self.db_checkbox.isChecked()
        
        if use_db:
            psd_plot = psd_to_db(self.psd_results)
            self.plot_widget.setLabel('left', 'PSD (dB)', color='#e0e0e0', size='12pt')
        else:
            psd_plot = self.psd_results
            self.plot_widget.setLabel('left', 'PSD', color='#e0e0e0', size='12pt')
        
        # Plot the PSD
        pen = pg.mkPen(color='#60a5fa', width=2)
        self.plot_widget.plot(self.frequencies, psd_plot, pen=pen)
        
        # Set log scale for x-axis (frequency)
        self.plot_widget.setLogMode(x=True, y=False)
