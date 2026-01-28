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
    QGroupBox, QGridLayout, QMessageBox, QCheckBox, QScrollArea, QTabWidget, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from pathlib import Path

# Import our custom modules
from spectral_edge.utils.data_loader import load_csv_data, DataLoadError
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.core.psd import (
    calculate_psd_welch, calculate_psd_maximax, psd_to_db, calculate_rms_from_psd, 
    get_window_options, convert_psd_to_octave_bands
)
from spectral_edge.core.channel_data import ChannelData, align_channels_by_time
from spectral_edge.gui.spectrogram_window import SpectrogramWindow
from spectral_edge.gui.event_manager import EventManagerWindow, Event
from spectral_edge.gui.flight_navigator import FlightNavigator
from spectral_edge.utils.message_box import show_information, show_warning, show_critical


class ScientificAxisItem(pg.AxisItem):
    """
    Custom axis item that always displays values in scientific notation.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)
    
    def tickStrings(self, values, scale, spacing):
        """
        Override tick string generation to always use scientific notation.
        
        Args:
            values: The tick values to display
            scale: The scale factor
            spacing: The spacing between ticks
        
        Returns:
            List of strings for tick labels in scientific notation
        """
        strings = []
        for v in values:
            # Convert from log scale to linear
            actual_value = 10 ** v
            
            # Format in scientific notation
            strings.append(f"{actual_value:.2e}")
        
        return strings


class PSDAnalysisWindow(QMainWindow):
    """
    Main window for PSD Analysis tool.
    
    This window provides a complete interface for:
    - Loading CSV data files
    - Configuring PSD calculation parameters
    - Computing and displaying PSD results
    - Interactive plotting with zoom and pan
    - Multi-channel selection and display
    - Time history visualization
    - Spectrogram generation
    """
    
    def __init__(self):
        """Initialize the PSD Analysis window."""
        super().__init__()
        
        # Window properties
        self.setWindowTitle("SpectralEdge - PSD Analysis")
        self.setMinimumSize(1400, 1000)
        
        # Data storage
        # Display data (decimated for plotting)
        self.time_data_display = None
        self.signal_data_display = None
        
        # Full resolution data (for calculations - NEVER decimated)
        self.time_data_full = None
        self.signal_data_full = None
        
        # Sample rate (always represents full resolution rate)
        self.channel_names = None
        self.channel_units = []  # Store units for each channel
        self.channel_flight_names = []  # Store flight name for each channel (for multi-flight HDF5)
        self.channel_sample_rates = []  # Store sample rate for each channel (for multi-rate support)
        self.sample_rate = None  # Reference sample rate (highest or first channel)
        self.current_file = None
        self.flight_name = ""  # Flight name for HDF5 data, empty for CSV
        
        # PSD results storage (dictionary keyed by channel name)
        self.frequencies = None
        self.psd_results = {}
        self.rms_values = {}
        
        # Channel selection checkboxes
        self.channel_checkboxes = []
        
        # Spectrogram windows
        self.spectrogram_windows = {}
        
        # Event management
        self.event_manager = None
        self.events = []  # List of Event objects
        self.event_regions = []  # List of LinearRegionItem for visualization
        self.interactive_selection_mode = False
        self.selection_start = None
        self.temp_selection_line = None
        
        # HDF5 data management
        self.hdf5_loader = None
        self.flight_navigator = None
        
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
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 8px;
                font-size: 13px;
                min-height: 25px;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                width: 20px;
                background-color: #3d4758;
                border: 1px solid #4a5568;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #4d5768;
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
            QScrollArea {
                border: none;
                background-color: #1a1f2e;
            }
            QWidget#channelWidget {
                background-color: #1a1f2e;
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
        
        # Right panel: Plots
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
        
        # File loading group (always visible at top)
        file_group = self._create_file_group()
        layout.addWidget(file_group)
        
        # Channel selection group (always visible)
        self.channel_group = self._create_channel_group()
        layout.addWidget(self.channel_group)
        
        # Create tabbed interface for parameters and options
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
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
            QTabBar::tab:hover {
                background-color: #3d4758;
            }
        """)
        
        # Tab 1: PSD Parameters
        params_tab = QWidget()
        params_layout = QVBoxLayout(params_tab)
        params_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        params_layout.addWidget(self._create_frequency_range_group())
        params_layout.addWidget(self._create_parameter_group())
        tab_widget.addTab(params_tab, "Parameters")
        
        # Tab 2: Display & Axes
        display_tab = QWidget()
        display_layout = QVBoxLayout(display_tab)
        display_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        display_layout.addWidget(self._create_display_options_group())
        display_layout.addWidget(self._create_axis_limits_group())
        tab_widget.addTab(display_tab, "Display")
        
        layout.addWidget(tab_widget)
        
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
        
        # Spectrogram button
        self.spec_button = QPushButton("Calculate Spectrogram")
        self.spec_button.setEnabled(False)
        self.spec_button.clicked.connect(self._open_spectrogram)
        layout.addWidget(self.spec_button)
        
        # Event Manager button
        self.event_button = QPushButton("Manage Events")
        self.event_button.setEnabled(False)
        self.event_button.clicked.connect(self._open_event_manager)
        layout.addWidget(self.event_button)
        
        # Clear Events button
        self.clear_events_button = QPushButton("Clear Events")
        self.clear_events_button.setEnabled(False)
        self.clear_events_button.setToolTip("Remove all events and reset to full data")
        self.clear_events_button.clicked.connect(self._clear_events)
        self.clear_events_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            QPushButton:disabled {
                background-color: #4a5568;
                color: #9ca3af;
            }
        """)
        layout.addWidget(self.clear_events_button)
        
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
        
        # Load CSV button
        load_csv_button = QPushButton("Load CSV File")
        load_csv_button.clicked.connect(self._load_file)
        layout.addWidget(load_csv_button)
        
        # Load HDF5 button
        load_hdf5_button = QPushButton("Load HDF5 File")
        load_hdf5_button.clicked.connect(self._load_hdf5_file)
        layout.addWidget(load_hdf5_button)
        
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
        scroll.setMinimumHeight(80)  # Minimum height for at least 2-3 channels
        scroll.setMaximumHeight(250)  # Increased from 150 to 250 for better visibility
        
        self.channel_widget = QWidget()
        self.channel_widget.setObjectName("channelWidget")  # For styling
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
        self.freq_min_spin.valueChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.freq_min_spin, 0, 1)
        
        # Max frequency
        layout.addWidget(QLabel("Max Freq (Hz):"), 1, 0)
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(1, 100000)
        self.freq_max_spin.setValue(2000.0)
        self.freq_max_spin.setDecimals(1)
        self.freq_max_spin.valueChanged.connect(self._on_parameter_changed)
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
        self.window_combo.currentTextChanged.connect(self._on_parameter_changed)
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
        self.df_spin.valueChanged.connect(self._on_parameter_changed)
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
        self.efficient_fft_checkbox.stateChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.efficient_fft_checkbox, row, 0, 1, 2)
        row += 1
        
        # Overlap percentage
        layout.addWidget(QLabel("Overlap (%):" ), row, 0)
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(50)
        self.overlap_spin.setSingleStep(10)
        self.overlap_spin.valueChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.overlap_spin, row, 1)
        row += 1
        
        # Maximax PSD checkbox
        self.maximax_checkbox = QCheckBox("Use Maximax PSD")
        self.maximax_checkbox.setChecked(True)  # Default to maximax
        self.maximax_checkbox.setToolTip("Calculate envelope PSD using sliding window maximax method (MPE-style)")
        self.maximax_checkbox.stateChanged.connect(self._on_maximax_toggled)
        self.maximax_checkbox.stateChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.maximax_checkbox, row, 0, 1, 2)
        row += 1
        
        # Maximax window duration
        layout.addWidget(QLabel("Maximax Window (s):" ), row, 0)
        self.maximax_window_spin = QDoubleSpinBox()
        self.maximax_window_spin.setRange(0.1, 10.0)
        self.maximax_window_spin.setValue(1.0)
        self.maximax_window_spin.setDecimals(1)
        self.maximax_window_spin.setSingleStep(0.5)
        self.maximax_window_spin.setToolTip("Duration of each maximax window in seconds")
        self.maximax_window_spin.valueChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.maximax_window_spin, row, 1)
        row += 1
        
        # Maximax overlap percentage
        layout.addWidget(QLabel("Maximax Overlap (%):" ), row, 0)
        self.maximax_overlap_spin = QSpinBox()
        self.maximax_overlap_spin.setRange(0, 90)
        self.maximax_overlap_spin.setValue(50)
        self.maximax_overlap_spin.setSingleStep(10)
        self.maximax_overlap_spin.setToolTip("Overlap percentage between maximax windows")
        self.maximax_overlap_spin.valueChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.maximax_overlap_spin, row, 1)
        row += 1
        
        group.setLayout(layout)
        return group
    
    def _create_display_options_group(self):
        """Create display options group."""
        group = QGroupBox("Display Options")
        layout = QVBoxLayout()
        
        # Show crosshair checkbox
        self.show_crosshair_checkbox = QCheckBox("Show Crosshair")
        self.show_crosshair_checkbox.setChecked(False)
        self.show_crosshair_checkbox.stateChanged.connect(self._toggle_crosshair)
        layout.addWidget(self.show_crosshair_checkbox)
        
        # Remove running mean checkbox
        self.remove_mean_checkbox = QCheckBox("Remove 1s Running Mean")
        self.remove_mean_checkbox.setChecked(False)
        self.remove_mean_checkbox.setToolTip("Remove 1-second running mean from time history to view vibration about mean")
        self.remove_mean_checkbox.stateChanged.connect(self._on_remove_mean_changed)
        layout.addWidget(self.remove_mean_checkbox)
        
        # Octave band display
        octave_layout = QHBoxLayout()
        self.octave_checkbox = QCheckBox("Octave Band Display")
        self.octave_checkbox.setChecked(False)
        self.octave_checkbox.setToolTip("Convert narrowband PSD to octave bands for visualization")
        self.octave_checkbox.stateChanged.connect(self._on_octave_display_changed)
        octave_layout.addWidget(self.octave_checkbox)
        
        # Octave fraction selector
        self.octave_combo = QComboBox()
        self.octave_combo.addItem("1/3 Octave", 3.0)
        self.octave_combo.addItem("1/6 Octave", 6.0)
        self.octave_combo.addItem("1/12 Octave", 12.0)
        self.octave_combo.addItem("1/24 Octave", 24.0)
        self.octave_combo.addItem("1/36 Octave", 36.0)
        self.octave_combo.setCurrentIndex(0)  # Default to 1/3 octave
        self.octave_combo.setEnabled(False)
        self.octave_combo.currentIndexChanged.connect(self._on_octave_fraction_changed)
        self.octave_combo.setToolTip("Select octave band spacing")
        octave_layout.addWidget(self.octave_combo)
        
        layout.addLayout(octave_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_axis_limits_group(self):
        """Create axis limits control group."""
        group = QGroupBox("Axis Limits")
        layout = QGridLayout()
        
        row = 0
        
        # X-axis limits (Frequency)
        layout.addWidget(QLabel("X-Axis (Hz):"), row, 0, 1, 2)
        row += 1
        
        layout.addWidget(QLabel("Min:"), row, 0)
        self.x_min_edit = QLineEdit()
        self.x_min_edit.setText("10.0")
        self.x_min_edit.setPlaceholderText("e.g., 10 or 1e1")
        self.x_min_edit.setToolTip("Enter frequency in Hz (standard or scientific notation)")
        layout.addWidget(self.x_min_edit, row, 1)
        row += 1
        
        layout.addWidget(QLabel("Max:"), row, 0)
        self.x_max_edit = QLineEdit()
        self.x_max_edit.setText("3000.0")
        self.x_max_edit.setPlaceholderText("e.g., 3000 or 3e3")
        self.x_max_edit.setToolTip("Enter frequency in Hz (standard or scientific notation)")
        layout.addWidget(self.x_max_edit, row, 1)
        row += 1
        
        # Y-axis limits (PSD)
        layout.addWidget(QLabel("Y-Axis (PSD):"), row, 0, 1, 2)
        row += 1
        
        layout.addWidget(QLabel("Min:"), row, 0)
        self.y_min_edit = QLineEdit()
        self.y_min_edit.setText("1e-7")
        self.y_min_edit.setPlaceholderText("e.g., 1e-7 or 0.0000001")
        self.y_min_edit.setToolTip("Enter PSD value (standard or scientific notation)")
        layout.addWidget(self.y_min_edit, row, 1)
        row += 1
        
        layout.addWidget(QLabel("Max:"), row, 0)
        self.y_max_edit = QLineEdit()
        self.y_max_edit.setText("10.0")
        self.y_max_edit.setPlaceholderText("e.g., 10 or 1e1")
        self.y_max_edit.setToolTip("Enter PSD value (standard or scientific notation)")
        layout.addWidget(self.y_max_edit, row, 1)
        row += 1
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Apply limits button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply_axis_limits)
        button_layout.addWidget(apply_button)
        
        # Auto-fit button
        auto_button = QPushButton("Auto-Fit")
        auto_button.clicked.connect(self._auto_fit_axes)
        button_layout.addWidget(auto_button)
        
        layout.addLayout(button_layout, row, 0, 1, 2)
        
        group.setLayout(layout)
        return group
    
    def _create_plot_panel(self):
        """Create the right plot panel with time history and PSD plots."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Time history plot
        self.time_plot_widget = pg.PlotWidget()
        self.time_plot_widget.setBackground('#1a1f2e')
        self.time_plot_widget.setLabel('left', 'Amplitude', color='#e0e0e0', size='11pt')
        self.time_plot_widget.setLabel('bottom', 'Time', units='s', color='#e0e0e0', size='11pt')
        self.time_plot_widget.setTitle("Time History", color='#60a5fa', size='12pt')
        self.time_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.time_plot_widget.setMouseEnabled(x=True, y=True)
        
        # Add legend for time plot with styled background
        self.time_legend = self.time_plot_widget.addLegend(offset=(10, 10))
        self.time_legend.setBrush(pg.mkBrush(26, 31, 46, 255))  # Solid GUI background
        self.time_legend.setPen(pg.mkPen(74, 85, 104, 255))  # Subtle border
        
        # Connect click event for interactive event selection
        self.time_plot_widget.scene().sigMouseClicked.connect(self._on_time_plot_clicked)
        
        layout.addWidget(self.time_plot_widget, stretch=1)
        
        # PSD plot with custom axes
        self.plot_widget = pg.PlotWidget(axisItems={
            'left': ScientificAxisItem(orientation='left')
        })
        self.plot_widget.setBackground('#1a1f2e')
        self.plot_widget.setLabel('left', 'PSD', units='', color='#e0e0e0', size='12pt')
        self.plot_widget.setLabel('bottom', 'Frequency (Hz)', color='#e0e0e0', size='12pt')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setTitle("Power Spectral Density", color='#60a5fa', size='14pt')
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.setLogMode(x=True, y=True)
        
        # Disable auto-range to prevent crosshair from panning
        self.plot_widget.getPlotItem().vb.disableAutoRange()
        
        # Add legend for PSD with styled background
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        self.legend.setBrush(pg.mkBrush(26, 31, 46, 255))  # Solid GUI background
        self.legend.setPen(pg.mkPen(74, 85, 104, 255))  # Subtle border
        
        # Configure axis appearance for full box border
        axis_pen = pg.mkPen(color='#4a5568', width=2)
        self.plot_widget.getPlotItem().getAxis('top').setPen(axis_pen)
        self.plot_widget.getPlotItem().getAxis('right').setPen(axis_pen)
        self.plot_widget.getPlotItem().getAxis('top').setStyle(showValues=False)
        self.plot_widget.getPlotItem().getAxis('right').setStyle(showValues=False)
        self.plot_widget.getPlotItem().showAxis('top')
        self.plot_widget.getPlotItem().showAxis('right')
        
        # Add crosshair for cursor position display
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#60a5fa', width=1, style=Qt.PenStyle.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#60a5fa', width=1, style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        
        # Add label for cursor coordinates
        self.coord_label = pg.TextItem(anchor=(0, 1), color='#e0e0e0')
        self.plot_widget.addItem(self.coord_label, ignoreBounds=True)
        
        # Connect mouse move event
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
        # Hide crosshair initially
        self.vLine.setVisible(False)
        self.hLine.setVisible(False)
        self.coord_label.setVisible(False)
        
        layout.addWidget(self.plot_widget, stretch=2)
        
        return panel
    
    def _toggle_crosshair(self):
        """Toggle crosshair visibility."""
        # Crosshair will only show when checkbox is checked AND mouse is over plot
        pass  # Actual visibility is handled in _on_mouse_moved
    
    def _on_mouse_moved(self, pos):
        """
        Handle mouse movement over the plot to show cursor coordinates.
        
        Args:
            pos: Mouse position in scene coordinates
        """
        # Only show if checkbox is checked
        if not self.show_crosshair_checkbox.isChecked():
            self.vLine.setVisible(False)
            self.hLine.setVisible(False)
            self.coord_label.setVisible(False)
            return
        
        # Check if mouse is within plot area
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            
            # Convert from log scale to linear
            freq = 10 ** mouse_point.x()
            psd = 10 ** mouse_point.y()
            
            # Update crosshair position
            self.vLine.setPos(mouse_point.x())
            self.hLine.setPos(mouse_point.y())
            self.vLine.setVisible(True)
            self.hLine.setVisible(True)
            
            # Update coordinate label
            if self.channel_units and self.channel_units[0]:
                unit = self.channel_units[0]
                label_text = f"f = {freq:.2f} Hz\nPSD = {psd:.3e} {unit}²/Hz"
            else:
                label_text = f"f = {freq:.2f} Hz\nPSD = {psd:.3e}"
            
            self.coord_label.setText(label_text)
            self.coord_label.setPos(mouse_point.x(), mouse_point.y())
            self.coord_label.setVisible(True)
        else:
            # Hide crosshair when mouse leaves plot area
            self.vLine.setVisible(False)
            self.hLine.setVisible(False)
            self.coord_label.setVisible(False)
    
    def _on_parameter_changed(self):
        """Handle parameter changes - clear PSD results to force recalculation."""
        # Clear PSD results
        self.frequencies = None
        self.psd_results = {}
        self.rms_values = {}
        
        # Clear the PSD plot but keep time history
        self._clear_psd_plot()
    
    def _clear_psd_plot(self):
        """Clear only the PSD plot."""
        self.plot_widget.clear()
        
        # Re-add crosshair and label
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        self.plot_widget.addItem(self.coord_label, ignoreBounds=True)
        
        # Re-add legend with styling
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        self.legend.setBrush(pg.mkBrush(26, 31, 46, 255))  # Solid GUI background
        self.legend.setPen(pg.mkPen(74, 85, 104, 255))
    
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
            time_data, signal_data, self.channel_names, self.sample_rate = \
                load_csv_data(file_path)
            
            # For CSV files, store same data for both full and display
            # (CSV files are typically small enough that no decimation is needed)
            self.time_data_full = time_data
            self.signal_data_full = signal_data
            self.time_data_display = time_data
            self.signal_data_display = signal_data
            
            self.current_file = Path(file_path).name
            self.flight_name = ""  # CSV data has no flight name
            self.channel_flight_names = []  # CSV data has no flight names
            
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
            duration = self.time_data_full[-1] - self.time_data_full[0]  # Use actual time span
            info_text = (f"Channels: {num_channels}\n"
                        f"Sample Rate: {self.sample_rate:.1f} Hz\n"
                        f"Duration: {duration:.2f} s\n"
                        f"Samples: {len(self.time_data_full)} (Full resolution)")
            self.info_label.setText(info_text)
            
            # Update nperseg calculation
            self._update_nperseg_from_df()
            
            # Create channel selection checkboxes
            self._create_channel_checkboxes()
            
            # Enable calculate buttons
            self.calc_button.setEnabled(True)
            self.spec_button.setEnabled(True)
            self.event_button.setEnabled(True)
            
            # Clear previous results
            self.frequencies = None
            self.psd_results = {}
            self.rms_values = {}
            
            # Plot time history
            self._plot_time_history()
            
        except (DataLoadError, FileNotFoundError) as e:
            show_critical(self, "Error Loading File", str(e))
        except Exception as e:
            show_critical(self, "Unexpected Error", f"An error occurred: {e}")
    
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
            checkbox.stateChanged.connect(self._on_channel_selection_changed)
            self.channel_layout.addWidget(checkbox)
            self.channel_checkboxes.append(checkbox)
        
        # Show the channel group
        self.channel_group.setVisible(True)
    
    def _on_channel_selection_changed(self):
        """Handle channel selection changes."""
        # Update both time history and PSD plots
        self._plot_time_history()
        self._update_plot()
    
    def _plot_time_history(self):
        """Plot time history of selected channels using decimated display data."""
        if self.signal_data_display is None:
            return
        
        # Clear previous plot
        self.time_plot_widget.clear()
        self.time_legend.clear()
        
        # Re-add legend with styling
        self.time_legend = self.time_plot_widget.addLegend(offset=(10, 10))
        self.time_legend.setBrush(pg.mkBrush(26, 31, 46, 255))  # Solid GUI background
        self.time_legend.setPen(pg.mkPen(74, 85, 104, 255))
        
        # Define colors for different channels
        colors = ['#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
        # Plot each selected channel
        plot_count = 0
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                channel_name = self.channel_names[i]
                # Get individual flight name for this channel
                flight_name = self.channel_flight_names[i] if i < len(self.channel_flight_names) else None
                
                # Use DISPLAY data (decimated) for plotting performance
                if self.signal_data_display.ndim == 1:
                    signal = self.signal_data_display.copy()
                else:
                    signal = self.signal_data_display[:, i].copy()
                
                # Apply running mean removal if checkbox is checked
                if self.remove_mean_checkbox.isChecked():
                    signal = self._remove_running_mean(signal, window_seconds=1.0)
                
                # Plot the time history
                color = colors[plot_count % len(colors)]
                pen = pg.mkPen(color=color, width=1.5)
                # Create legend label with individual flight name if available
                if flight_name:
                    legend_label = f"{flight_name} - {channel_name}"
                else:
                    legend_label = channel_name
                
                # Add suffix to legend if running mean removed
                if self.remove_mean_checkbox.isChecked():
                    legend_label += " (mean removed)"
                
                self.time_plot_widget.plot(
                    self.time_data_display,
                    signal,
                    pen=pen,
                    name=legend_label
                )
                
                plot_count += 1
        
        # Update Y-axis label with units
        if self.channel_units and self.channel_units[0]:
            unit = self.channel_units[0]
            self.time_plot_widget.setLabel('left', f'Amplitude ({unit})', color='#e0e0e0', size='11pt')
        else:
            self.time_plot_widget.setLabel('left', 'Amplitude', color='#e0e0e0', size='11pt')
    
    def _calculate_psd(self):
        """Calculate PSD with current parameters for all channels using FULL RESOLUTION data."""
        if self.signal_data_full is None:
            return
        
        try:
            # Get parameters from UI
            window = self.window_combo.currentText().lower()
            df = self.df_spin.value()
            overlap_percent = self.overlap_spin.value()
            
            # Get frequency range for RMS calculation
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()
            
            # Limit freq_max to Nyquist frequency (sample_rate / 2)
            nyquist_freq = self.sample_rate / 2.0
            if freq_max > nyquist_freq:
                freq_max = nyquist_freq
                # Update the spinbox to show the limited value
                self.freq_max_spin.setValue(freq_max)
                show_information(self, "Frequency Range Adjusted", 
                    f"Maximum frequency adjusted to Nyquist limit: {nyquist_freq:.2f} Hz\n\n"
                    f"Sample rate: {self.sample_rate} Hz\n"
                    f"Nyquist frequency: {nyquist_freq:.2f} Hz\n\n"
                    f"PSD will be calculated up to {nyquist_freq:.2f} Hz.")
            
            # Determine number of channels and shape
            if self.signal_data_full.ndim == 1:
                num_channels = 1
            else:
                num_channels = self.signal_data_full.shape[1]  # samples x channels
            
            self.psd_results = {}
            self.rms_values = {}
            
            # Calculate PSD for each channel using FULL RESOLUTION data
            for channel_idx in range(num_channels):
                channel_name = self.channel_names[channel_idx]
                
                # Get this channel's sample rate (support for multi-rate)
                if self.channel_sample_rates and len(self.channel_sample_rates) > channel_idx:
                    channel_sample_rate = self.channel_sample_rates[channel_idx]
                else:
                    channel_sample_rate = self.sample_rate  # Fallback to reference rate
                
                # Extract signal for this channel from FULL resolution data
                if self.signal_data_full.ndim == 1:
                    signal = self.signal_data_full
                else:
                    signal = self.signal_data_full[:, channel_idx]
                
                # Calculate PSD (maximax or traditional)
                if self.maximax_checkbox.isChecked():
                    # Use maximax PSD calculation
                    maximax_window = self.maximax_window_spin.value()
                    maximax_overlap = self.maximax_overlap_spin.value()
                    
                    frequencies, psd = calculate_psd_maximax(
                        signal,
                        channel_sample_rate,  # Use channel-specific sample rate
                        df=df,
                        maximax_window=maximax_window,
                        overlap_percent=maximax_overlap,
                        window=window
                    )
                else:
                    # Use traditional averaged PSD
                    # Calculate nperseg from df for overlap calculation
                    nperseg = int(channel_sample_rate / df)  # Use channel-specific sample rate
                    noverlap = int(nperseg * overlap_percent / 100.0)
                    
                    frequencies, psd = calculate_psd_welch(
                        signal,
                        channel_sample_rate,  # Use channel-specific sample rate
                        df=df,
                        noverlap=noverlap,
                        window=window
                    )
                
                # Store full frequency range (same for all channels)
                if self.frequencies is None:
                    self.frequencies = frequencies
                
                # Store PSD for this channel
                self.psd_results[channel_name] = psd
                
                # Calculate RMS over specified frequency range
                rms = calculate_rms_from_psd(
                    frequencies, 
                    psd, 
                    freq_min=freq_min, 
                    freq_max=freq_max
                )
                
                self.rms_values[channel_name] = rms
            
            # Update plot
            self._update_plot()
            
        except Exception as e:
            show_critical(self, "Calculation Error", f"Failed to calculate PSD: {e}\n\nPlease try adjusting the frequency resolution or frequency range.")
    
    def _set_frequency_ticks(self):
        """Set frequency axis ticks to only show powers of 10."""
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
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
        
        # Set the ticks on the bottom axis
        bottom_axis = self.plot_widget.getPlotItem().getAxis('bottom')
        bottom_axis.setTicks([[(val, label) for val, label in zip(tick_values, tick_labels)]])
    
    def _update_plot(self):
        """Update the PSD plot with selected channels."""
        if self.frequencies is None or not self.psd_results:
            return
        
        # Clear previous plot
        self._clear_psd_plot()
        
        # Get frequency range for plotting
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Filter frequencies for plotting
        freq_mask = (self.frequencies >= freq_min) & (self.frequencies <= freq_max)
        
        # Check if mask has any True values
        if not np.any(freq_mask):
            show_warning(self, "No Data", "No frequency data in the specified range. Please adjust the frequency range.")
            return
        
        frequencies_plot = self.frequencies[freq_mask]
        
        # Define colors for different channels
        colors = ['#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
        # Check if octave band display is enabled
        use_octave = self.octave_checkbox.isChecked()
        octave_fraction = self.octave_combo.currentData() if use_octave else None
        
        # Plot each selected channel
        plot_count = 0
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                channel_name = self.channel_names[i]
                
                # Check if PSD exists for this channel
                if channel_name not in self.psd_results:
                    continue
                
                psd = self.psd_results[channel_name][freq_mask]
                rms = self.rms_values[channel_name]
                unit = self.channel_units[i] if i < len(self.channel_units) else ''
                # Get individual flight name for this channel
                flight_name = self.channel_flight_names[i] if i < len(self.channel_flight_names) else None
                
                # Convert to octave bands if requested
                if use_octave and octave_fraction is not None:
                    try:
                        frequencies_plot_oct, psd_oct = convert_psd_to_octave_bands(
                            frequencies_plot,
                            psd,
                            octave_fraction=octave_fraction,
                            freq_min=freq_min,
                            freq_max=freq_max
                        )
                        frequencies_to_plot = frequencies_plot_oct
                        psd_to_plot = psd_oct
                        # Add octave info to legend with individual flight name
                        octave_name = self.octave_combo.currentText()
                        if flight_name:
                            if unit:
                                legend_label = f"{flight_name} - {channel_name} ({octave_name}): RMS={rms:.4f} {unit}"
                            else:
                                legend_label = f"{flight_name} - {channel_name} ({octave_name}): RMS={rms:.4f}"
                        else:
                            if unit:
                                legend_label = f"{channel_name} ({octave_name}): RMS={rms:.4f} {unit}"
                            else:
                                legend_label = f"{channel_name} ({octave_name}): RMS={rms:.4f}"
                    except Exception as e:
                        show_warning(self, "Octave Conversion Error", f"Failed to convert to octave bands: {str(e)}\nShowing narrowband data.")
                        frequencies_to_plot = frequencies_plot
                        psd_to_plot = psd
                        if flight_name:
                            if unit:
                                legend_label = f"{flight_name} - {channel_name}: RMS={rms:.4f} {unit}"
                            else:
                                legend_label = f"{flight_name} - {channel_name}: RMS={rms:.4f}"
                        else:
                            if unit:
                                legend_label = f"{channel_name}: RMS={rms:.4f} {unit}"
                            else:
                                legend_label = f"{channel_name}: RMS={rms:.4f}"
                else:
                    frequencies_to_plot = frequencies_plot
                    psd_to_plot = psd
                    # Create legend label with RMS and individual flight name
                    if flight_name:
                        if unit:
                            legend_label = f"{flight_name} - {channel_name}: RMS={rms:.4f} {unit}"
                        else:
                            legend_label = f"{flight_name} - {channel_name}: RMS={rms:.4f}"
                    else:
                        if unit:
                            legend_label = f"{channel_name}: RMS={rms:.4f} {unit}"
                        else:
                            legend_label = f"{channel_name}: RMS={rms:.4f}"
                
                # Plot the PSD
                color = colors[plot_count % len(colors)]
                pen = pg.mkPen(color=color, width=2)
                
                # Use bar plot for octave bands, line plot for narrowband
                if use_octave:
                    # Use combined markers and lines for octave bands
                    # This ensures connectivity even with sparse data points
                    self.plot_widget.plot(
                        frequencies_to_plot,
                        psd_to_plot,
                        pen=pg.mkPen(color=color, width=1.5),  # Solid line connecting points
                        symbol='o',
                        symbolSize=8,
                        symbolBrush=color,
                        symbolPen=pg.mkPen(color=color, width=1),
                        name=legend_label
                    )
                else:
                    self.plot_widget.plot(
                        frequencies_to_plot, 
                        psd_to_plot, 
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
        
        # Apply axis limits from controls
        self._apply_axis_limits()
    
    def _open_spectrogram(self):
        """Open spectrogram window for selected channels (up to 4) using FULL RESOLUTION data."""
        if self.signal_data_full is None:
            return
        
        # Find all selected channels
        selected_channels = []
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                selected_channels.append(i)
        
        if len(selected_channels) == 0:
            show_warning(self, "No Channel Selected", "Please select at least one channel to generate spectrogram.")
            return
        
        # Warn if more than 4 channels selected
        if len(selected_channels) > 4:
            show_warning(
                self, 
                "Too Many Channels", 
                f"You have selected {len(selected_channels)} channels. "
                "Only the first 4 will be displayed in the spectrogram window."
            )
            selected_channels = selected_channels[:4]
        
        # Prepare data for selected channels
        channels_data = []
        channel_sample_rates_list = []  # Store sample rate for each selected channel
        for idx in selected_channels:
            channel_name = self.channel_names[idx]
            # Use FULL resolution data for spectrogram calculations
            if self.signal_data_full.ndim == 1:
                signal = self.signal_data_full
            else:
                signal = self.signal_data_full[:, idx]
            unit = self.channel_units[idx] if idx < len(self.channel_units) else ''
            # Get flight name for this specific channel (empty for CSV)
            flight_name = self.channel_flight_names[idx] if idx < len(self.channel_flight_names) else ''
            # Get sample rate for this channel
            if self.channel_sample_rates and idx < len(self.channel_sample_rates):
                channel_sr = self.channel_sample_rates[idx]
            else:
                channel_sr = self.sample_rate  # Fallback
            channels_data.append((channel_name, signal, unit, flight_name))
            channel_sample_rates_list.append(channel_sr)
        
        # Get current PSD parameters to pass to spectrogram
        window = self.window_combo.currentText().lower()
        df = self.df_spin.value()
        overlap_percent = self.overlap_spin.value()
        efficient_fft = self.efficient_fft_checkbox.isChecked()
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Create unique key for this channel combination
        channels_key = "_".join([name for name, _, _, _ in channels_data])
        
        # Create or show spectrogram window
        if channels_key in self.spectrogram_windows:
            window_obj = self.spectrogram_windows[channels_key]
            window_obj.show()
            window_obj.raise_()
            window_obj.activateWindow()
        else:
            window_obj = SpectrogramWindow(
                self.time_data_full,
                channels_data,  # Pass list of (name, signal, unit, flight_name) tuples
                channel_sample_rates_list,  # Pass list of sample rates (one per channel)
                window_type=window,
                df=df,
                overlap_percent=overlap_percent,
                efficient_fft=efficient_fft,
                freq_min=freq_min,
                freq_max=freq_max
            )
            window_obj.show()
            self.spectrogram_windows[channels_key] = window_obj
    
    def _open_event_manager(self):
        """Open the Event Manager window."""
        if self.time_data_full is None:
            return
        
        # Create event manager if it doesn't exist
        if self.event_manager is None:
            max_time = self.time_data_full[-1]
            self.event_manager = EventManagerWindow(max_time=max_time)
            
            # Connect signals
            self.event_manager.events_updated.connect(self._on_events_updated)
            self.event_manager.interactive_mode_changed.connect(self._on_interactive_mode_changed)
        
        # Show the window
        self.event_manager.show()
        self.event_manager.raise_()
        self.event_manager.activateWindow()
    
    def _on_events_updated(self, events):
        """
        Handle events updated from Event Manager.
        
        Args:
            events: List of Event objects
        """
        self.events = events
        
        # Enable/disable clear events button based on whether events exist
        # Don't count the "Full" event as it's always present
        non_full_events = [e for e in events if e.name != "Full"]
        self.clear_events_button.setEnabled(len(non_full_events) > 0)
        
        # Update visualization
        self._update_event_regions()
        
        # Calculate PSDs for all events
        self._calculate_event_psds()
    
    def _on_interactive_mode_changed(self, enabled):
        """
        Handle interactive selection mode toggle.
        
        Args:
            enabled: True if interactive mode is enabled
        """
        self.interactive_selection_mode = enabled
        
        # Reset selection state
        self.selection_start = None
        if self.temp_selection_line is not None:
            self.time_plot_widget.removeItem(self.temp_selection_line)
            self.temp_selection_line = None
    
    def _on_time_plot_clicked(self, event):
        """
        Handle click on time history plot for interactive event selection.
        
        Args:
            event: Mouse click event
        """
        if not self.interactive_selection_mode:
            return
        
        # Check if click is within plot area
        if not self.time_plot_widget.sceneBoundingRect().contains(event.scenePos()):
            return
        
        # Get time value at click position
        mouse_point = self.time_plot_widget.plotItem.vb.mapSceneToView(event.scenePos())
        time_value = mouse_point.x()
        
        # Clamp to valid range
        time_value = max(0, min(time_value, self.time_data_full[-1]))
        
        if self.selection_start is None:
            # First click - set start time
            self.selection_start = time_value
            
            # Add temporary vertical line
            self.temp_selection_line = pg.InfiniteLine(
                pos=time_value,
                angle=90,
                pen=pg.mkPen('#60a5fa', width=2, style=Qt.PenStyle.DashLine),
                label='Start'
            )
            self.time_plot_widget.addItem(self.temp_selection_line)
        
        else:
            # Second click - set end time and create event
            end_time = time_value
            
            # Remove temporary line
            if self.temp_selection_line is not None:
                self.time_plot_widget.removeItem(self.temp_selection_line)
                self.temp_selection_line = None
            
            # Ensure start < end
            if self.selection_start > end_time:
                self.selection_start, end_time = end_time, self.selection_start
            
            # Add event to Event Manager
            if self.event_manager is not None:
                self.event_manager.add_event_from_selection(self.selection_start, end_time)
            
            # Reset selection
            self.selection_start = None
    
    def _update_event_regions(self):
        """Update visual representation of events on time history plot."""
        # Remove existing regions
        for region in self.event_regions:
            self.time_plot_widget.removeItem(region)
        self.event_regions.clear()
        
        # Add new regions
        colors = [
            (96, 165, 250, 50),   # Blue
            (16, 185, 129, 50),   # Green
            (245, 158, 11, 50),   # Orange
            (239, 68, 68, 50),    # Red
            (139, 92, 246, 50),   # Purple
            (236, 72, 153, 50),   # Pink
        ]
        
        for i, event in enumerate(self.events):
            # Skip "Full" event
            if event.name == "Full":
                continue
            
            color = colors[i % len(colors)]
            
            # Create shaded region
            region = pg.LinearRegionItem(
                values=[event.start_time, event.end_time],
                brush=pg.mkBrush(*color),
                pen=pg.mkPen(color[:3] + (150,), width=2),
                movable=False
            )
            
            self.time_plot_widget.addItem(region)
            self.event_regions.append(region)
    
    def _calculate_event_psds(self):
        """Calculate PSDs for all defined events using FULL RESOLUTION data."""
        if self.signal_data_full is None or not self.events:
            return
        
        try:
            # Get parameters from UI
            window = self.window_combo.currentText().lower()
            df = self.df_spin.value()
            overlap_percent = self.overlap_spin.value()
            
            # Get frequency range for RMS calculation
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()
            
            # Limit freq_max to Nyquist frequency (sample_rate / 2)
            nyquist_freq = self.sample_rate / 2.0
            if freq_max > nyquist_freq:
                freq_max = nyquist_freq
                # Update the spinbox to show the limited value
                self.freq_max_spin.setValue(freq_max)
                show_information(self, "Frequency Range Adjusted", 
                    f"Maximum frequency adjusted to Nyquist limit: {nyquist_freq:.2f} Hz\n\n"
                    f"Sample rate: {self.sample_rate} Hz\n"
                    f"Nyquist frequency: {nyquist_freq:.2f} Hz\n\n"
                    f"PSD will be calculated up to {nyquist_freq:.2f} Hz.")
            
            # Determine number of channels
            if self.signal_data_full.ndim == 1:
                num_channels = 1
            else:
                num_channels = self.signal_data_full.shape[1]
            
            # Clear previous results
            self.psd_results = {}
            self.rms_values = {}
            
            # Calculate PSD for each event and channel
            for event in self.events:
                # Get time indices for this event using FULL resolution time data
                start_idx = int(event.start_time * self.sample_rate)
                end_idx = int(event.end_time * self.sample_rate)
                
                # Clamp to valid range
                start_idx = max(0, start_idx)
                end_idx = min(len(self.time_data_full), end_idx)
                
                # Calculate PSD for each channel
                for channel_idx in range(num_channels):
                    channel_name = self.channel_names[channel_idx]
                    
                    # Extract signal segment from FULL resolution data
                    if self.signal_data_full.ndim == 1:
                        signal_segment = self.signal_data_full[start_idx:end_idx]
                    else:
                        signal_segment = self.signal_data_full[start_idx:end_idx, channel_idx]
                    
                    # Calculate PSD using updated function signature
                    # Calculate nperseg from df for overlap calculation
                    nperseg = int(self.sample_rate / df)
                    noverlap = int(nperseg * overlap_percent / 100.0)
                    
                    frequencies, psd = calculate_psd_welch(
                        signal_segment,
                        self.sample_rate,
                        df=df,
                        noverlap=noverlap,
                        window=window
                    )
                    
                    # Store full frequency range (same for all)
                    if self.frequencies is None:
                        self.frequencies = frequencies
                    
                    # Create unique key for event + channel
                    key = f"{event.name}_{channel_name}"
                    
                    # Store PSD for this event and channel
                    self.psd_results[key] = psd
                    
                    # Calculate RMS over specified frequency range
                    rms = calculate_rms_from_psd(
                        frequencies,
                        psd,
                        freq_min=freq_min,
                        freq_max=freq_max
                    )
                    
                    self.rms_values[key] = rms
            
            # Update plot
            self._update_plot_with_events()
            
        except Exception as e:
            show_critical(self, "Calculation Error", f"Failed to calculate event PSDs: {e}")
    
    def _update_plot_with_events(self):
        """Update the PSD plot with event-based PSDs."""
        if self.frequencies is None or not self.psd_results:
            return
        
        # Clear previous plot
        self._clear_psd_plot()
        
        # Get frequency range for plotting
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Filter frequencies for plotting
        freq_mask = (self.frequencies >= freq_min) & (self.frequencies <= freq_max)
        
        if not np.any(freq_mask):
            show_warning(self, "No Data", "No frequency data in the specified range.")
            return
        
        frequencies_plot = self.frequencies[freq_mask]
        
        # Define colors for different events
        colors = ['#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
        # Plot PSDs for each event and selected channel
        plot_count = 0
        for event in self.events:
            for i, checkbox in enumerate(self.channel_checkboxes):
                if checkbox.isChecked():
                    channel_name = self.channel_names[i]
                    key = f"{event.name}_{channel_name}"
                    
                    # Check if PSD exists for this event + channel
                    if key not in self.psd_results:
                        continue
                    
                    psd = self.psd_results[key][freq_mask]
                    rms = self.rms_values[key]
                    unit = self.channel_units[i] if i < len(self.channel_units) else ''
                    
                    # Create legend label with event name, channel, and RMS
                    if len(self.events) > 1:
                        # Show event name when multiple events
                        if unit:
                            legend_label = f"{event.name} - {channel_name}: RMS={rms:.4f} {unit}"
                        else:
                            legend_label = f"{event.name} - {channel_name}: RMS={rms:.4f}"
                    else:
                        # Just channel name for single event
                        if unit:
                            legend_label = f"{channel_name}: RMS={rms:.4f} {unit}"
                        else:
                            legend_label = f"{channel_name}: RMS={rms:.4f}"
                    
                    # Plot the PSD
                    color = colors[plot_count % len(colors)]
                    
                    # Use dashed line for "Full" event
                    if event.name == "Full":
                        pen = pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine)
                    else:
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
        
        # Set X-axis range
        self.plot_widget.setXRange(np.log10(freq_min), np.log10(freq_max))
        
        # Set custom frequency ticks
        self._set_frequency_ticks()
        
        # Disable auto-range
        self.plot_widget.getPlotItem().vb.enableAutoRange(enable=False)
    
    def _apply_axis_limits(self):
        """Apply user-specified axis limits to the PSD plot."""
        # Get limits from text fields and parse
        try:
            x_min = float(self.x_min_edit.text())
            x_max = float(self.x_max_edit.text())
            y_min = float(self.y_min_edit.text())
            y_max = float(self.y_max_edit.text())
        except ValueError as e:
            show_warning(self, "Invalid Input", 
                        f"Please enter valid numbers (standard or scientific notation).\nError: {e}")
            return
        
        # Validate limits
        if x_min >= x_max:
            show_warning(self, "Invalid Limits", "X-axis minimum must be less than maximum.")
            return
        
        if y_min >= y_max:
            show_warning(self, "Invalid Limits", "Y-axis minimum must be less than maximum.")
            return
        
        # Validate positive values for log scale
        if x_min <= 0 or x_max <= 0:
            show_warning(self, "Invalid Limits", "X-axis limits must be positive for log scale.")
            return
        
        if y_min <= 0 or y_max <= 0:
            show_warning(self, "Invalid Limits", "Y-axis limits must be positive for log scale.")
            return
        
        # Set X-axis range (log scale)
        try:
            log_x_min = np.log10(x_min)
            log_x_max = np.log10(x_max)
            if np.isfinite(log_x_min) and np.isfinite(log_x_max):
                self.plot_widget.setXRange(log_x_min, log_x_max)
            else:
                show_warning(self, "Invalid Range", "X-axis range resulted in invalid log values.")
                return
        except Exception as e:
            show_warning(self, "Error", f"Failed to set X-axis range: {e}")
            return
        
        # Set Y-axis range (log scale)
        try:
            log_y_min = np.log10(y_min)
            log_y_max = np.log10(y_max)
            if np.isfinite(log_y_min) and np.isfinite(log_y_max):
                self.plot_widget.setYRange(log_y_min, log_y_max)
            else:
                show_warning(self, "Invalid Range", "Y-axis range resulted in invalid log values.")
                return
        except Exception as e:
            show_warning(self, "Error", f"Failed to set Y-axis range: {e}")
            return
        
        # Update frequency ticks
        self._set_frequency_ticks()
        
        # Disable auto-range to maintain user-specified limits
        self.plot_widget.getPlotItem().vb.enableAutoRange(enable=False)
    
    def _auto_fit_axes(self):
        """Auto-fit axes based on current data."""
        if self.frequencies is None or not self.psd_results:
            show_information(self, "No Data", "Please calculate PSD first before using auto-fit.")
            return
        
        # Get frequency range from data
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Filter frequencies
        freq_mask = (self.frequencies >= freq_min) & (self.frequencies <= freq_max)
        
        if not np.any(freq_mask):
            show_warning(self, "No Data", "No data in the specified frequency range.")
            return
        
        # Find min/max PSD values across all selected channels
        psd_min = np.inf
        psd_max = -np.inf
        
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                channel_name = self.channel_names[i]
                
                if channel_name in self.psd_results:
                    psd = self.psd_results[channel_name][freq_mask]
                    
                    # Filter out zeros and negative values for log scale
                    psd_positive = psd[psd > 0]
                    
                    if len(psd_positive) > 0:
                        psd_min = min(psd_min, np.min(psd_positive))
                        psd_max = max(psd_max, np.max(psd_positive))
        
        # If we found valid data, update limits
        if psd_min != np.inf and psd_max != -np.inf:
            # Add some margin (10% on log scale)
            log_range = np.log10(psd_max) - np.log10(psd_min)
            margin = log_range * 0.1
            
            y_min_auto = 10 ** (np.log10(psd_min) - margin)
            y_max_auto = 10 ** (np.log10(psd_max) + margin)
            
            # Update text fields
            self.y_min_edit.setText(f"{y_min_auto:.2e}")
            self.y_max_edit.setText(f"{y_max_auto:.2e}")
            
            # Apply the new limits
            self._apply_axis_limits()
        else:
            show_warning(self, "No Valid Data", "No positive PSD values found for auto-fit.")
    
    def _load_hdf5_file(self):
        """Load HDF5 file and open flight navigator."""
        try:
            # Open file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load HDF5 File",
                str(Path.home()),
                "HDF5 Files (*.hdf5 *.h5);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Close existing loader if any
            if self.hdf5_loader is not None:
                self.hdf5_loader.close()
            
            # Create new loader
            self.hdf5_loader = HDF5FlightDataLoader(file_path)
            
            # Open flight navigator
            self.flight_navigator = FlightNavigator(self.hdf5_loader, self)
            self.flight_navigator.data_selected.connect(self._on_hdf5_data_selected)
            self.flight_navigator.show()
            
        except Exception as e:
            show_critical(self, "Load Error", f"Failed to load HDF5 file: {e}")
    
    def _on_hdf5_data_selected(self, selected_items):
        """
        Handle data selection from flight navigator.
        
        Parameters:
        -----------
        selected_items : list of tuples
            List of (flight_key, channel_key, channel_info) tuples
        """
        try:
            print("\n=== HDF5 DATA LOADING DEBUG ===")
            print(f"Selected items: {len(selected_items)}")
            
            if not selected_items:
                print("No items selected")
                return
            
            # Load all selected channels
            print(f"Loading {len(selected_items)} channel(s)...")
            
            all_signals_full = []
            all_signals_display = []
            all_channel_names = []
            all_channel_units = []
            all_sample_rates = []  # Store sample rate for each channel
            time_data_full = None
            time_data_display = None
            sample_rate = None  # Reference sample rate (will be max of all)
            decimation_factor = 1
            flight_info = []
            
            # First pass: collect all data and find max sample rate
            channel_data_list = []
            for idx, (flight_key, channel_key, channel_info) in enumerate(selected_items):
                print(f"\nChannel {idx+1}/{len(selected_items)}:")
                print(f"  Flight key: {flight_key}")
                print(f"  Channel key: {channel_key}")
                print(f"  Sample rate: {channel_info.sample_rate} Hz")
                
                # Load data - returns dict with both full and decimated data
                result = self.hdf5_loader.load_channel_data(flight_key, channel_key, decimate_for_display=True)
                print(f"  Full data: time shape={result['time_full'].shape}, signal shape={result['data_full'].shape}")
                print(f"  Display data: time shape={result['time_display'].shape}, signal shape={result['data_display'].shape}")
                print(f"  Decimation factor: {result.get('decimation_factor', 1)}")
                
                channel_data_list.append({
                    'result': result,
                    'channel_key': channel_key,
                    'flight_key': flight_key,
                    'units': channel_info.units
                })
                
                # Track max sample rate
                if sample_rate is None or result['sample_rate'] > sample_rate:
                    sample_rate = result['sample_rate']
                    decimation_factor = result.get('decimation_factor', 1)
            
            print(f"\nReference sample rate (max): {sample_rate} Hz")
            
            # Second pass: align time data if needed
            for idx, ch_data in enumerate(channel_data_list):
                result = ch_data['result']
                
                # Store first channel's time as reference
                if time_data_full is None:
                    time_data_full = result['time_full']
                    time_data_display = result['time_display']
                
                # Check if sample rates differ
                if result['sample_rate'] != sample_rate:
                    print(f"  Channel {idx+1}: Different sample rate {result['sample_rate']} Hz (reference: {sample_rate} Hz)")
                    print(f"    Multi-rate support: Each channel will use its own sample rate for PSD calculation")
                
                all_signals_full.append(result['data_full'])
                all_signals_display.append(result['data_display'])
                all_channel_names.append(ch_data['channel_key'])
                all_channel_units.append(ch_data['units'])
                all_sample_rates.append(result['sample_rate'])  # Store each channel's sample rate
                flight_info.append(ch_data['flight_key'])
            
            # Align signal lengths with zero-padding if needed
            if len(all_signals_full) > 1:
                # Find maximum length
                max_len_full = max(len(sig) for sig in all_signals_full)
                max_len_display = max(len(sig) for sig in all_signals_display)
                
                # Zero-pad shorter signals to match longest
                all_signals_full_padded = []
                all_signals_display_padded = []
                
                for i, (sig_full, sig_display) in enumerate(zip(all_signals_full, all_signals_display)):
                    if len(sig_full) < max_len_full:
                        # Pad with zeros at the end
                        padded_full = np.pad(sig_full, (0, max_len_full - len(sig_full)), mode='constant', constant_values=0)
                        print(f"    Channel {i+1}: Padded from {len(sig_full)} to {max_len_full} samples")
                    else:
                        padded_full = sig_full
                    
                    if len(sig_display) < max_len_display:
                        padded_display = np.pad(sig_display, (0, max_len_display - len(sig_display)), mode='constant', constant_values=0)
                    else:
                        padded_display = sig_display
                    
                    all_signals_full_padded.append(padded_full)
                    all_signals_display_padded.append(padded_display)
                
                # Stack signals into 2D array (samples x channels)
                self.signal_data_full = np.column_stack(all_signals_full_padded)
                self.signal_data_display = np.column_stack(all_signals_display_padded)
            else:
                # Single channel - no padding needed
                self.signal_data_full = all_signals_full[0].reshape(-1, 1)
                self.signal_data_display = all_signals_display[0].reshape(-1, 1)
            self.time_data_full = time_data_full
            self.time_data_display = time_data_display
            self.sample_rate = sample_rate  # Reference sample rate (max)
            self.channel_names = all_channel_names
            self.channel_units = all_channel_units
            self.channel_sample_rates = all_sample_rates  # Store each channel's sample rate
            self.channel_flight_names = flight_info  # Store flight name for each channel
            
            # Create file label and set flight name
            if len(set(flight_info)) == 1:
                self.current_file = f"{flight_info[0]} ({len(selected_items)} channels)"
                self.flight_name = flight_info[0]  # Single flight name
            else:
                self.current_file = f"Multiple flights ({len(selected_items)} channels)"
                self.flight_name = "Multiple flights"  # Multiple flights
            
            print(f"\nFinal full data shape: {self.signal_data_full.shape}")
            print(f"Final display data shape: {self.signal_data_display.shape}")
            print(f"Time data full shape: {self.time_data_full.shape}")
            print(f"Time data display shape: {self.time_data_display.shape}")
            
            # Calculate duration from full resolution time vector
            duration = self.time_data_full[-1] - self.time_data_full[0]
            
            # Update UI
            self.file_label.setText(f"Loaded: {self.current_file}")
            if decimation_factor > 1:
                self.info_label.setText(
                    f"Sample Rate: {self.sample_rate:.0f} Hz | "
                    f"Duration: {duration:.2f} s | "
                    f"Channels: {len(self.channel_names)} | "
                    f"Decimated {decimation_factor}x for display"
                )
            else:
                self.info_label.setText(
                    f"Sample Rate: {self.sample_rate:.0f} Hz | "
                    f"Duration: {duration:.2f} s | "
                    f"Channels: {len(self.channel_names)} (Full resolution)"
                )
            
            # Show channel selection group
            self.channel_group.setVisible(True)
            
            # Clear previous channel checkboxes
            for checkbox in self.channel_checkboxes:
                checkbox.deleteLater()
            self.channel_checkboxes.clear()
            
            # Create checkboxes for all channels
            for i, (name, unit, sr) in enumerate(zip(self.channel_names, self.channel_units, self.channel_sample_rates)):
                # Include sample rate if channels have different rates
                if len(set(self.channel_sample_rates)) > 1:
                    display_name = f"{name} ({unit}, {sr:.0f} Hz)" if unit else f"{name} ({sr:.0f} Hz)"
                else:
                    display_name = f"{name} ({unit})" if unit else name
                checkbox = QCheckBox(display_name)
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(self._plot_time_history)
                self.channel_layout.addWidget(checkbox)
                self.channel_checkboxes.append(checkbox)
            
            # Enable buttons
            self.calc_button.setEnabled(True)
            self.spec_button.setEnabled(True)
            self.event_button.setEnabled(True)
            
            # Clear previous results
            self.frequencies = None
            self.psd_results = {}
            self.rms_values = {}
            self._clear_psd_plot()
            
            # Update time history plot
            self._plot_time_history()
            
            # Update nperseg display
            self._update_nperseg_from_df()
            
            # Create message based on decimation
            if decimation_factor > 1:
                message = (
                    f"Successfully loaded {len(self.channel_names)} channel(s)\n"
                    f"Channels: {', '.join(self.channel_names)}\n"
                    f"Sample Rate: {self.sample_rate:.0f} Hz\n"
                    f"Duration: {duration:.2f} seconds\n"
                    f"Samples: {len(self.time_data_full)} (full), {len(self.time_data_display)} (display)\n\n"
                    f"Note: Data decimated {decimation_factor}x for display.\n"
                    f"Full resolution will be used for PSD calculations."
                )
            else:
                message = (
                    f"Successfully loaded {len(self.channel_names)} channel(s)\n"
                    f"Channels: {', '.join(self.channel_names)}\n"
                    f"Sample Rate: {self.sample_rate:.0f} Hz\n"
                    f"Duration: {duration:.2f} seconds\n"
                    f"Samples: {len(self.time_data_full)} (full resolution)"
                )
            
            show_information(self, "Data Loaded", message)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"\n=== ERROR IN HDF5 LOADING ===")
            print(error_details)
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            show_critical(self, "Load Error", f"Failed to load HDF5 data: {e}\n\nSee console for full traceback.")
    
    def _on_maximax_toggled(self):
        """Handle maximax checkbox toggle."""
        is_maximax = self.maximax_checkbox.isChecked()
        
        # Enable/disable maximax-specific controls
        self.maximax_window_spin.setEnabled(is_maximax)
        self.maximax_overlap_spin.setEnabled(is_maximax)
        
        # Update tooltip on calculate button
        if is_maximax:
            self.calc_button.setToolTip(
                "Calculate Maximax PSD (envelope of sliding window PSDs)"
            )
        else:
            self.calc_button.setToolTip(
                "Calculate averaged PSD using Welch's method"
            )

    
    def _on_octave_display_changed(self):
        """Handle octave band display checkbox state change."""
        is_enabled = self.octave_checkbox.isChecked()
        self.octave_combo.setEnabled(is_enabled)
        
        # Re-plot if we have data
        if self.frequencies is not None and self.psd_results:
            self._update_plot()
    
    def _on_octave_fraction_changed(self):
        """Handle octave fraction selection change."""
        # Re-plot if we have data and octave display is enabled
        if self.octave_checkbox.isChecked() and self.frequencies is not None and self.psd_results:
            self._update_plot()

    def _remove_running_mean(self, signal, window_seconds=1.0):
        """
        Remove running mean from signal using a moving average filter.
        
        This function computes a running mean over a specified window duration
        and subtracts it from the signal, making it easier to visualize the
        vibration content about the mean.
        
        Parameters
        ----------
        signal : np.ndarray
            Input signal array (1D).
            Type: float64 array
            Units: Same as input signal (e.g., g for acceleration)
            
        window_seconds : float, optional
            Duration of the running mean window in seconds.
            Type: float
            Units: seconds
            Default: 1.0 (1 second window)
            Typical range: 0.1 to 5.0 seconds
            
        Returns
        -------
        signal_detrended : np.ndarray
            Signal with running mean removed.
            Type: float64 array
            Shape: Same as input signal
            Units: Same as input signal
            
        Notes
        -----
        - Uses uniform (boxcar) filter for running mean calculation
        - Window size in samples = window_seconds * sample_rate
        - Edge effects handled using 'same' mode (pads edges)
        - Does NOT affect PSD calculation (only for visualization)
        - Running mean is calculated on DISPLAY data (decimated)
        
        Examples
        --------
        >>> # Remove 1-second running mean from accelerometer data
        >>> signal_with_mean = np.array([1.0, 1.1, 0.9, 1.0, 1.1])  # 1 g + noise
        >>> signal_detrended = self._remove_running_mean(signal_with_mean, window_seconds=1.0)
        >>> # Result: [-0.02, 0.08, -0.12, -0.02, 0.08] (vibration about mean)
        
        References
        ----------
        - scipy.ndimage.uniform_filter1d: https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.uniform_filter1d.html
        """
        from scipy.ndimage import uniform_filter1d
        
        # Calculate window size in samples
        # Use display sample rate (may be decimated)
        display_sample_rate = len(self.time_data_display) / (self.time_data_display[-1] - self.time_data_display[0])
        window_samples = int(window_seconds * display_sample_rate)
        
        # Ensure window size is at least 3 samples and odd
        window_samples = max(3, window_samples)
        if window_samples % 2 == 0:
            window_samples += 1
        
        # Compute running mean using uniform filter
        running_mean = uniform_filter1d(signal, size=window_samples, mode='nearest')
        
        # Subtract running mean from signal
        signal_detrended = signal - running_mean
        
        return signal_detrended
    
    def _on_remove_mean_changed(self):
        """Handle running mean removal checkbox state change."""
        # Simply re-plot the time history with or without running mean removal
        self._plot_time_history()

    def _clear_events(self):
        """Clear all events and reset plots to full data."""
        # Clear events list (keep only "Full" event if it exists)
        self.events = [e for e in self.events if e.name == "Full"]
        
        # Clear event regions from time plot
        for region in self.event_regions:
            self.time_plot_widget.removeItem(region)
        self.event_regions.clear()
        
        # Disable clear events button
        self.clear_events_button.setEnabled(False)
        
        # Update event manager if it exists
        if self.event_manager is not None:
            self.event_manager.clear_all_events()
        
        # Reset interactive selection mode
        self.interactive_selection_mode = False
        self.selection_start = None
        if self.temp_selection_line is not None:
            self.time_plot_widget.removeItem(self.temp_selection_line)
            self.temp_selection_line = None
        
        # Clear event-based PSD results
        self.psd_results = {}
        self.rms_values = {}
        self.frequencies = None
        
        # Clear PSD plot
        self._clear_psd_plot()
        
        # Show information message
        show_information(self, "Events Cleared", "All events have been removed. Click 'Calculate PSD' to recalculate with full data.")
