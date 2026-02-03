"""
Batch Processor Setup GUI

This module provides a comprehensive GUI for setting up and running batch PSD processing.
Integrates with the Enhanced Flight Navigator for channel selection from HDF5 files.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QGroupBox, QCheckBox, QDoubleSpinBox, QSpinBox, QComboBox,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QDoubleValidator


class ScientificDoubleSpinBox(QDoubleSpinBox):
    """
    A QDoubleSpinBox that displays values in scientific notation.

    Ideal for PSD values that span many orders of magnitude.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDecimals(10)  # Internal precision
        self._decimals_display = 2  # Display precision for scientific notation

    def textFromValue(self, value: float) -> str:
        """Convert value to scientific notation string."""
        if value == 0:
            return "0.00e+00"
        return f"{value:.{self._decimals_display}e}"

    def valueFromText(self, text: str) -> float:
        """Convert scientific notation string to value."""
        try:
            return float(text)
        except ValueError:
            return self.value()

    def validate(self, text: str, pos: int):
        """Validate scientific notation input."""
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
        return validator.validate(text, pos)

from spectral_edge.batch.config import (
    BatchConfig, FilterConfig, PSDConfig, SpectrogramConfig,
    DisplayConfig, OutputConfig, EventDefinition
)
from spectral_edge.batch.processor import BatchProcessor
from spectral_edge.batch.batch_worker import BatchWorker
from spectral_edge.gui.flight_navigator_enhanced import EnhancedFlightNavigator
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.utils.message_box import show_information, show_warning, show_critical, show_question

logger = logging.getLogger(__name__)


class BatchProcessorWindow(QMainWindow):
    """
    Main window for batch PSD processing setup and execution.
    
    Provides a comprehensive interface for:
    - File selection (HDF5 or CSV)
    - Channel selection via Enhanced Flight Navigator
    - Event definition
    - Parameter configuration (PSD, filter, spectrogram, display)
    - Output format selection
    - Configuration save/load
    - Batch execution with progress tracking
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.config = BatchConfig()
        self.selected_channels = []
        self.batch_worker = None
        self.processing_log = []
        
        self._init_ui()
        self._connect_signals()
        
        logger.info("Batch Processor Window initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Batch PSD Processor")
        self.setGeometry(100, 100, 1200, 800)

        # Apply dark theme styling to match PSD GUI
        self._apply_dark_theme()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Batch PSD Processor Setup")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Tab widget for configuration sections
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_data_source_tab()
        self._create_events_tab()
        self._create_psd_parameters_tab()
        self._create_filter_tab()
        self._create_spectrogram_tab()
        self._create_display_tab()
        self._create_output_tab()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
        
        # Control buttons
        button_layout = QHBoxLayout()

        self.load_config_btn = QPushButton("Load Configuration")
        self.save_config_btn = QPushButton("Save Configuration")
        self.run_batch_btn = QPushButton("▶ Run Batch Processing")
        self.run_batch_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:disabled {
                background-color: #4a5568;
            }
        """)

        self.cancel_btn = QPushButton("⏹ Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:disabled {
                background-color: #4a5568;
            }
        """)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)

        button_layout.addWidget(self.load_config_btn)
        button_layout.addWidget(self.save_config_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.run_batch_btn)

        main_layout.addLayout(button_layout)
    
    def _create_data_source_tab(self):
        """Create the data source selection tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Source type selection
        source_group = QGroupBox("Data Source")
        source_layout = QVBoxLayout()
        
        # HDF5 option
        hdf5_layout = QHBoxLayout()
        self.hdf5_radio = QCheckBox("HDF5 File(s)")
        self.hdf5_radio.setChecked(True)
        self.select_hdf5_btn = QPushButton("Select HDF5 Files")
        hdf5_layout.addWidget(self.hdf5_radio)
        hdf5_layout.addWidget(self.select_hdf5_btn)
        hdf5_layout.addStretch()
        source_layout.addLayout(hdf5_layout)
        
        # CSV option
        csv_layout = QHBoxLayout()
        self.csv_radio = QCheckBox("CSV File(s)")
        self.select_csv_btn = QPushButton("Select CSV Files")
        csv_layout.addWidget(self.csv_radio)
        csv_layout.addWidget(self.select_csv_btn)
        csv_layout.addStretch()
        source_layout.addLayout(csv_layout)
        
        # Selected files display
        self.files_text = QTextEdit()
        self.files_text.setReadOnly(True)
        self.files_text.setMaximumHeight(100)
        source_layout.addWidget(QLabel("Selected Files:"))
        source_layout.addWidget(self.files_text)
        
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # Channel selection (for HDF5)
        channel_group = QGroupBox("Channel Selection (HDF5 only)")
        channel_layout = QVBoxLayout()
        
        self.select_channels_btn = QPushButton("Open Enhanced Flight Navigator")
        self.select_channels_btn.setStyleSheet("padding: 10px; font-weight: bold;")
        channel_layout.addWidget(self.select_channels_btn)
        
        self.channels_text = QTextEdit()
        self.channels_text.setReadOnly(True)
        self.channels_text.setMaximumHeight(150)
        channel_layout.addWidget(QLabel("Selected Channels:"))
        channel_layout.addWidget(self.channels_text)
        
        channel_group.setLayout(channel_layout)
        layout.addWidget(channel_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Data Source")
    
    def _create_events_tab(self):
        """Create the events definition tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Process full duration option
        self.full_duration_checkbox = QCheckBox("Process Full Duration (no events)")
        self.full_duration_checkbox.setChecked(True)
        layout.addWidget(self.full_duration_checkbox)
        
        # Events table
        events_group = QGroupBox("Event Definitions")
        events_layout = QVBoxLayout()
        
        self.events_table = QTableWidget(0, 4)
        self.events_table.setHorizontalHeaderLabels(["Event Name", "Start Time (s)", "End Time (s)", "Description"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        events_layout.addWidget(self.events_table)
        
        # Event control buttons
        event_btn_layout = QHBoxLayout()
        self.add_event_btn = QPushButton("Add Event")
        self.remove_event_btn = QPushButton("Remove Selected")
        self.clear_events_btn = QPushButton("Clear All")
        event_btn_layout.addWidget(self.add_event_btn)
        event_btn_layout.addWidget(self.remove_event_btn)
        event_btn_layout.addWidget(self.clear_events_btn)
        event_btn_layout.addStretch()
        events_layout.addLayout(event_btn_layout)
        
        events_group.setLayout(events_layout)
        layout.addWidget(events_group)
        
        self.tab_widget.addTab(tab, "Events")
    
    def _create_psd_parameters_tab(self):
        """Create the PSD parameters configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # PSD method
        method_group = QGroupBox("PSD Calculation Method")
        method_layout = QHBoxLayout()
        self.psd_method_combo = QComboBox()
        self.psd_method_combo.addItems(["welch", "maximax"])
        method_layout.addWidget(QLabel("Method:"))
        method_layout.addWidget(self.psd_method_combo)
        method_layout.addStretch()
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)
        
        # Window and overlap
        window_group = QGroupBox("Window Settings")
        window_layout = QVBoxLayout()
        
        window_row1 = QHBoxLayout()
        self.window_combo = QComboBox()
        self.window_combo.addItems(["hann", "hamming", "blackman", "bartlett"])
        window_row1.addWidget(QLabel("Window:"))
        window_row1.addWidget(self.window_combo)
        window_row1.addStretch()
        window_layout.addLayout(window_row1)
        
        window_row2 = QHBoxLayout()
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 99)
        self.overlap_spin.setValue(50)
        self.overlap_spin.setSuffix(" %")
        self.overlap_spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        window_row2.addWidget(QLabel("Overlap:"))
        window_row2.addWidget(self.overlap_spin)
        window_row2.addStretch()
        window_layout.addLayout(window_row2)
        
        window_group.setLayout(window_layout)
        layout.addWidget(window_group)
        
        # Frequency settings
        freq_group = QGroupBox("Frequency Settings")
        freq_layout = QVBoxLayout()
        
        freq_row1 = QHBoxLayout()
        self.df_spin = QDoubleSpinBox()
        self.df_spin.setRange(0.01, 100.0)
        self.df_spin.setValue(1.0)
        self.df_spin.setDecimals(2)
        self.df_spin.setSuffix(" Hz")
        self.df_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        freq_row1.addWidget(QLabel("Desired Δf:"))
        freq_row1.addWidget(self.df_spin)
        self.efficient_fft_checkbox = QCheckBox("Use efficient FFT size")
        self.efficient_fft_checkbox.setChecked(True)
        freq_row1.addWidget(self.efficient_fft_checkbox)
        freq_row1.addStretch()
        freq_layout.addLayout(freq_row1)
        
        freq_row2 = QHBoxLayout()
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0.1, 100000.0)
        self.freq_min_spin.setValue(20.0)
        self.freq_min_spin.setSuffix(" Hz")
        self.freq_min_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(1.0, 100000.0)
        self.freq_max_spin.setValue(2000.0)
        self.freq_max_spin.setSuffix(" Hz")
        self.freq_max_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        freq_row2.addWidget(QLabel("Frequency Range:"))
        freq_row2.addWidget(self.freq_min_spin)
        freq_row2.addWidget(QLabel("to"))
        freq_row2.addWidget(self.freq_max_spin)
        freq_row2.addStretch()
        freq_layout.addLayout(freq_row2)
        
        freq_row3 = QHBoxLayout()
        self.freq_spacing_combo = QComboBox()
        self.freq_spacing_combo.addItems(["linear", "octave"])
        freq_row3.addWidget(QLabel("Frequency Spacing:"))
        freq_row3.addWidget(self.freq_spacing_combo)
        freq_row3.addStretch()
        freq_layout.addLayout(freq_row3)
        
        freq_group.setLayout(freq_layout)
        layout.addWidget(freq_group)
        
        # Mean removal
        self.remove_mean_checkbox = QCheckBox("Remove Running Mean (1s window)")
        self.remove_mean_checkbox.setChecked(True)
        layout.addWidget(self.remove_mean_checkbox)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "PSD Parameters")
    
    def _create_filter_tab(self):
        """Create the filter configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Enable filtering
        self.filter_enabled_checkbox = QCheckBox("Enable Signal Filtering")
        layout.addWidget(self.filter_enabled_checkbox)
        
        # Filter settings
        filter_group = QGroupBox("Filter Settings")
        filter_layout = QVBoxLayout()
        
        # Filter type
        type_row = QHBoxLayout()
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(["lowpass", "highpass", "bandpass"])
        type_row.addWidget(QLabel("Filter Type:"))
        type_row.addWidget(self.filter_type_combo)
        type_row.addStretch()
        filter_layout.addLayout(type_row)
        
        # Filter design
        design_row = QHBoxLayout()
        self.filter_design_combo = QComboBox()
        self.filter_design_combo.addItems(["butterworth", "chebyshev", "bessel"])
        design_row.addWidget(QLabel("Filter Design:"))
        design_row.addWidget(self.filter_design_combo)
        design_row.addStretch()
        filter_layout.addLayout(design_row)
        
        # Filter order
        order_row = QHBoxLayout()
        self.filter_order_spin = QSpinBox()
        self.filter_order_spin.setRange(1, 10)
        self.filter_order_spin.setValue(4)
        self.filter_order_spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        order_row.addWidget(QLabel("Filter Order:"))
        order_row.addWidget(self.filter_order_spin)
        order_row.addStretch()
        filter_layout.addLayout(order_row)
        
        # Cutoff frequencies
        cutoff_row = QHBoxLayout()
        self.cutoff_low_spin = QDoubleSpinBox()
        self.cutoff_low_spin.setRange(0.1, 100000.0)
        self.cutoff_low_spin.setValue(100.0)
        self.cutoff_low_spin.setSuffix(" Hz")
        self.cutoff_low_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.cutoff_high_spin = QDoubleSpinBox()
        self.cutoff_high_spin.setRange(0.1, 100000.0)
        self.cutoff_high_spin.setValue(2000.0)
        self.cutoff_high_spin.setSuffix(" Hz")
        self.cutoff_high_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        cutoff_row.addWidget(QLabel("Cutoff Low:"))
        cutoff_row.addWidget(self.cutoff_low_spin)
        cutoff_row.addWidget(QLabel("Cutoff High:"))
        cutoff_row.addWidget(self.cutoff_high_spin)
        cutoff_row.addStretch()
        filter_layout.addLayout(cutoff_row)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Filter")
    
    def _create_spectrogram_tab(self):
        """Create the spectrogram configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Enable spectrograms
        self.spectrogram_enabled_checkbox = QCheckBox("Generate Spectrograms")
        layout.addWidget(self.spectrogram_enabled_checkbox)
        
        # Spectrogram settings
        spec_group = QGroupBox("Spectrogram Settings")
        spec_layout = QVBoxLayout()
        
        # Parameters
        param_row1 = QHBoxLayout()
        self.spec_df_spin = QDoubleSpinBox()
        self.spec_df_spin.setRange(0.01, 100.0)
        self.spec_df_spin.setValue(1.0)
        self.spec_df_spin.setDecimals(2)
        self.spec_df_spin.setSuffix(" Hz")
        self.spec_df_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        param_row1.addWidget(QLabel("Desired Δf:"))
        param_row1.addWidget(self.spec_df_spin)
        param_row1.addStretch()
        spec_layout.addLayout(param_row1)
        
        param_row2 = QHBoxLayout()
        self.spec_overlap_spin = QSpinBox()
        self.spec_overlap_spin.setRange(0, 99)
        self.spec_overlap_spin.setValue(50)
        self.spec_overlap_spin.setSuffix(" %")
        self.spec_overlap_spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        param_row2.addWidget(QLabel("Overlap:"))
        param_row2.addWidget(self.spec_overlap_spin)
        param_row2.addStretch()
        spec_layout.addLayout(param_row2)
        
        param_row3 = QHBoxLayout()
        self.spec_snr_spin = QSpinBox()
        self.spec_snr_spin.setRange(0, 100)
        self.spec_snr_spin.setValue(20)
        self.spec_snr_spin.setSuffix(" dB")
        self.spec_snr_spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        param_row3.addWidget(QLabel("SNR Threshold:"))
        param_row3.addWidget(self.spec_snr_spin)
        param_row3.addStretch()
        spec_layout.addLayout(param_row3)
        
        # Colormap
        colormap_row = QHBoxLayout()
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["viridis", "plasma", "inferno", "magma", "cividis", "jet"])
        colormap_row.addWidget(QLabel("Colormap:"))
        colormap_row.addWidget(self.colormap_combo)
        colormap_row.addStretch()
        spec_layout.addLayout(colormap_row)
        
        spec_group.setLayout(spec_layout)
        layout.addWidget(spec_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Spectrogram")
    
    def _create_display_tab(self):
        """Create the display settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # PSD plot settings
        psd_group = QGroupBox("PSD Plot Display Settings")
        psd_layout = QVBoxLayout()
        
        self.psd_auto_scale_checkbox = QCheckBox("Auto-scale axes")
        psd_layout.addWidget(self.psd_auto_scale_checkbox)
        
        # X-axis limits
        x_axis_row = QHBoxLayout()
        self.psd_x_min_spin = QDoubleSpinBox()
        self.psd_x_min_spin.setRange(0.1, 100000.0)
        self.psd_x_min_spin.setValue(10.0)
        self.psd_x_min_spin.setSuffix(" Hz")
        self.psd_x_min_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.psd_x_max_spin = QDoubleSpinBox()
        self.psd_x_max_spin.setRange(1.0, 100000.0)
        self.psd_x_max_spin.setValue(3000.0)
        self.psd_x_max_spin.setSuffix(" Hz")
        self.psd_x_max_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        x_axis_row.addWidget(QLabel("X-axis (Frequency):"))
        x_axis_row.addWidget(self.psd_x_min_spin)
        x_axis_row.addWidget(QLabel("to"))
        x_axis_row.addWidget(self.psd_x_max_spin)
        x_axis_row.addStretch()
        psd_layout.addLayout(x_axis_row)
        
        # Y-axis limits (scientific notation for PSD values)
        y_axis_row = QHBoxLayout()
        self.psd_y_min_spin = ScientificDoubleSpinBox()
        self.psd_y_min_spin.setRange(1e-15, 1e10)
        self.psd_y_min_spin.setValue(1e-5)
        self.psd_y_min_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.psd_y_min_spin.setMinimumWidth(100)
        self.psd_y_max_spin = ScientificDoubleSpinBox()
        self.psd_y_max_spin.setRange(1e-15, 1e10)
        self.psd_y_max_spin.setValue(10.0)
        self.psd_y_max_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.psd_y_max_spin.setMinimumWidth(100)
        y_axis_row.addWidget(QLabel("Y-axis (PSD):"))
        y_axis_row.addWidget(self.psd_y_min_spin)
        y_axis_row.addWidget(QLabel("to"))
        y_axis_row.addWidget(self.psd_y_max_spin)
        y_axis_row.addStretch()
        psd_layout.addLayout(y_axis_row)
        
        # Legend and grid
        options_row = QHBoxLayout()
        self.psd_show_legend_checkbox = QCheckBox("Show Legend")
        self.psd_show_legend_checkbox.setChecked(True)
        self.psd_show_grid_checkbox = QCheckBox("Show Grid")
        self.psd_show_grid_checkbox.setChecked(True)
        options_row.addWidget(self.psd_show_legend_checkbox)
        options_row.addWidget(self.psd_show_grid_checkbox)
        options_row.addStretch()
        psd_layout.addLayout(options_row)
        
        psd_group.setLayout(psd_layout)
        layout.addWidget(psd_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Display")
    
    def _create_output_tab(self):
        """Create the output format selection tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Output directory
        dir_group = QGroupBox("Output Directory")
        dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory...")
        self.select_output_dir_btn = QPushButton("Browse")
        dir_layout.addWidget(self.output_dir_edit)
        dir_layout.addWidget(self.select_output_dir_btn)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # Output formats
        format_group = QGroupBox("Output Formats")
        format_layout = QVBoxLayout()
        
        self.excel_checkbox = QCheckBox("Excel (.xlsx) - One sheet per event")
        self.excel_checkbox.setChecked(True)
        format_layout.addWidget(self.excel_checkbox)
        
        self.csv_checkbox = QCheckBox("CSV - One file per event")
        self.csv_checkbox.setChecked(True)
        format_layout.addWidget(self.csv_checkbox)
        
        self.powerpoint_checkbox = QCheckBox("PowerPoint (.pptx) - Report with plots")
        self.powerpoint_checkbox.setChecked(True)
        format_layout.addWidget(self.powerpoint_checkbox)
        
        self.hdf5_checkbox = QCheckBox("HDF5 Write-back - Append to source file (HDF5 only)")
        self.hdf5_checkbox.setChecked(True)
        format_layout.addWidget(self.hdf5_checkbox)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Output")
    
    def _connect_signals(self):
        """Connect signals to slots."""
        # File selection
        self.select_hdf5_btn.clicked.connect(self._on_select_hdf5)
        self.select_csv_btn.clicked.connect(self._on_select_csv)
        self.select_channels_btn.clicked.connect(self._on_select_channels)
        
        # Events
        self.add_event_btn.clicked.connect(self._on_add_event)
        self.remove_event_btn.clicked.connect(self._on_remove_event)
        self.clear_events_btn.clicked.connect(self._on_clear_events)
        
        # Output directory
        self.select_output_dir_btn.clicked.connect(self._on_select_output_dir)
        
        # Configuration
        self.load_config_btn.clicked.connect(self._on_load_config)
        self.save_config_btn.clicked.connect(self._on_save_config)

        # Run batch and cancel
        self.run_batch_btn.clicked.connect(self._on_run_batch)
        self.cancel_btn.clicked.connect(self._on_cancel_batch)

    def _apply_dark_theme(self):
        """Apply dark theme styling to match the PSD GUI."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1f2e;
            }
            QWidget {
                background-color: #1a1f2e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QGroupBox {
                color: #60a5fa;
                font-weight: bold;
                border: 2px solid #4a5568;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #60a5fa;
            }
            QTabWidget::pane {
                border: 2px solid #4a5568;
                border-radius: 5px;
                background-color: #1a1f2e;
            }
            QTabBar::tab {
                background-color: #2d3748;
                color: #e0e0e0;
                padding: 8px 16px;
                border: 1px solid #4a5568;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1a1f2e;
                color: #60a5fa;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #374151;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #4a5568;
                color: #9ca3af;
            }
            QLineEdit, QTextEdit {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                border-radius: 4px;
                padding: 4px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #60a5fa;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                border-radius: 4px;
                padding: 4px;
                padding-right: 20px;
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
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 5px solid #e0e0e0;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
            }
            QComboBox {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox::drop-down {
                background-color: #4a5568;
                border: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d3748;
                color: #e0e0e0;
                selection-background-color: #2563eb;
                border: 1px solid #4a5568;
            }
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #4a5568;
                border-radius: 3px;
                background-color: #2d3748;
            }
            QCheckBox::indicator:checked {
                background-color: #2563eb;
                border-color: #2563eb;
            }
            QCheckBox::indicator:hover {
                border-color: #60a5fa;
            }
            QTableWidget {
                background-color: #2d3748;
                color: #e0e0e0;
                gridline-color: #4a5568;
                border: 1px solid #4a5568;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #2563eb;
            }
            QHeaderView::section {
                background-color: #1a1f2e;
                color: #60a5fa;
                padding: 8px;
                border: 1px solid #4a5568;
                font-weight: bold;
            }
            QProgressBar {
                background-color: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 5px;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background-color: #1a1f2e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a5568;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #60a5fa;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #1a1f2e;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4a5568;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #60a5fa;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            /* File Dialog Styling for readability */
            QFileDialog {
                background-color: #1a1f2e;
                color: #e0e0e0;
            }
            QFileDialog QWidget {
                background-color: #1a1f2e;
                color: #e0e0e0;
            }
            QFileDialog QListView, QFileDialog QTreeView {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                selection-background-color: #2563eb;
            }
            QFileDialog QListView::item, QFileDialog QTreeView::item {
                color: #e0e0e0;
                padding: 4px;
            }
            QFileDialog QListView::item:selected, QFileDialog QTreeView::item:selected {
                background-color: #2563eb;
                color: white;
            }
            QFileDialog QLineEdit {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                border-radius: 4px;
                padding: 4px;
            }
            QFileDialog QComboBox {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
            }
            QFileDialog QToolButton {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
            }
            QFileDialog QHeaderView::section {
                background-color: #1a1f2e;
                color: #60a5fa;
                border: 1px solid #4a5568;
            }
            QFileDialog QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
            }
            QFileDialog QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)

    def _on_select_hdf5(self):
        """Handle HDF5 file selection."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select HDF5 Files",
            "",
            "HDF5 Files (*.h5 *.hdf5);;All Files (*)"
        )
        
        if files:
            self.config.source_type = "hdf5"
            self.config.source_files = files
            self.files_text.setText("\n".join(files))
            self.hdf5_radio.setChecked(True)
            self.csv_radio.setChecked(False)
            logger.info(f"Selected {len(files)} HDF5 file(s)")
    
    def _on_select_csv(self):
        """Handle CSV file selection."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select CSV Files",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if files:
            self.config.source_type = "csv"
            self.config.source_files = files
            self.files_text.setText("\n".join(files))
            self.csv_radio.setChecked(True)
            self.hdf5_radio.setChecked(False)
            logger.info(f"Selected {len(files)} CSV file(s)")
    
    def _on_select_channels(self):
        """Open Enhanced Flight Navigator for channel selection."""
        if not self.config.source_files or self.config.source_type != "hdf5":
            show_warning(
                self,
                "No HDF5 Files Selected",
                "Please select HDF5 files first before choosing channels."
            )
            return
        
        # Open Enhanced Flight Navigator
        try:
            loader = HDF5FlightDataLoader(self.config.source_files[0])
            navigator = EnhancedFlightNavigator(loader, parent=self)
        except Exception as e:
            show_critical(
                self,
                "Error Loading HDF5 File",
                f"Failed to load HDF5 file: {str(e)}"
            )
            return
        
        if navigator.exec() == navigator.DialogCode.Accepted:
            self.selected_channels = navigator.get_selected_channels()
            self.config.selected_channels = self.selected_channels
            
            # Display selected channels
            channel_text = "\n".join([f"{flight}/{channel}" for flight, channel in self.selected_channels])
            self.channels_text.setText(channel_text)
            logger.info(f"Selected {len(self.selected_channels)} channel(s)")
    
    def _on_add_event(self):
        """Add a new event to the table."""
        row = self.events_table.rowCount()
        self.events_table.insertRow(row)
        
        # Set default values
        self.events_table.setItem(row, 0, QTableWidgetItem(f"event_{row+1}"))
        self.events_table.setItem(row, 1, QTableWidgetItem("0.0"))
        self.events_table.setItem(row, 2, QTableWidgetItem("10.0"))
        self.events_table.setItem(row, 3, QTableWidgetItem(""))
    
    def _on_remove_event(self):
        """Remove selected event from the table."""
        current_row = self.events_table.currentRow()
        if current_row >= 0:
            self.events_table.removeRow(current_row)
    
    def _on_clear_events(self):
        """Clear all events from the table."""
        self.events_table.setRowCount(0)
    
    def _on_select_output_dir(self):
        """Select output directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )
        
        if directory:
            self.output_dir_edit.setText(directory)
            self.config.output_config.output_directory = directory
    
    def _on_load_config(self):
        """Load configuration from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                self.config = BatchConfig.load(file_path)
                self._populate_ui_from_config()
                show_information(self, "Configuration Loaded", f"Configuration loaded from:\n{file_path}")
                logger.info(f"Configuration loaded from: {file_path}")
            except Exception as e:
                show_critical(self, "Load Failed", f"Failed to load configuration:\n{str(e)}")
                logger.error(f"Failed to load configuration: {str(e)}")
    
    def _on_save_config(self):
        """Save configuration to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                self._update_config_from_ui()
                self.config.save(file_path)
                show_information(self, "Configuration Saved", f"Configuration saved to:\n{file_path}")
                logger.info(f"Configuration saved to: {file_path}")
            except Exception as e:
                show_critical(self, "Save Failed", f"Failed to save configuration:\n{str(e)}")
                logger.error(f"Failed to save configuration: {str(e)}")
    
    def _on_run_batch(self):
        """Run batch processing."""
        try:
            # Update configuration from UI
            self._update_config_from_ui()
            
            # Validate configuration
            self.config.validate()
            
            # Start batch processing in worker thread
            self._start_batch_processing()
            
        except ValueError as e:
            show_warning(self, "Invalid Configuration", f"Configuration validation failed:\n{str(e)}")
            logger.warning(f"Configuration validation failed: {str(e)}")
        except Exception as e:
            show_critical(self, "Error", f"An error occurred:\n{str(e)}")
            logger.error(f"Error in batch processing: {str(e)}")
    
    def _update_config_from_ui(self):
        """Update configuration object from UI controls."""
        # Events
        self.config.process_full_duration = self.full_duration_checkbox.isChecked()
        self.config.events = []
        
        for row in range(self.events_table.rowCount()):
            event = EventDefinition(
                name=self.events_table.item(row, 0).text(),
                start_time=float(self.events_table.item(row, 1).text()),
                end_time=float(self.events_table.item(row, 2).text()),
                description=self.events_table.item(row, 3).text() if self.events_table.item(row, 3) else ""
            )
            self.config.events.append(event)
        
        # PSD config
        self.config.psd_config.method = self.psd_method_combo.currentText()
        self.config.psd_config.window = self.window_combo.currentText()
        self.config.psd_config.overlap_percent = float(self.overlap_spin.value())
        self.config.psd_config.use_efficient_fft = self.efficient_fft_checkbox.isChecked()
        self.config.psd_config.desired_df = self.df_spin.value()
        self.config.psd_config.freq_min = self.freq_min_spin.value()
        self.config.psd_config.freq_max = self.freq_max_spin.value()
        self.config.psd_config.frequency_spacing = self.freq_spacing_combo.currentText()
        self.config.psd_config.remove_running_mean = self.remove_mean_checkbox.isChecked()
        
        # Filter config
        self.config.filter_config.enabled = self.filter_enabled_checkbox.isChecked()
        self.config.filter_config.filter_type = self.filter_type_combo.currentText()
        self.config.filter_config.filter_design = self.filter_design_combo.currentText()
        self.config.filter_config.filter_order = self.filter_order_spin.value()
        self.config.filter_config.cutoff_low = self.cutoff_low_spin.value()
        self.config.filter_config.cutoff_high = self.cutoff_high_spin.value()
        
        # Spectrogram config
        self.config.spectrogram_config.enabled = self.spectrogram_enabled_checkbox.isChecked()
        self.config.spectrogram_config.desired_df = self.spec_df_spin.value()
        self.config.spectrogram_config.overlap_percent = float(self.spec_overlap_spin.value())
        self.config.spectrogram_config.snr_threshold = float(self.spec_snr_spin.value())
        self.config.spectrogram_config.colormap = self.colormap_combo.currentText()
        
        # Display config
        self.config.display_config.psd_auto_scale = self.psd_auto_scale_checkbox.isChecked()
        self.config.display_config.psd_x_axis_min = self.psd_x_min_spin.value()
        self.config.display_config.psd_x_axis_max = self.psd_x_max_spin.value()
        self.config.display_config.psd_y_axis_min = self.psd_y_min_spin.value()
        self.config.display_config.psd_y_axis_max = self.psd_y_max_spin.value()
        self.config.display_config.psd_show_legend = self.psd_show_legend_checkbox.isChecked()
        self.config.display_config.psd_show_grid = self.psd_show_grid_checkbox.isChecked()
        
        # Output config
        self.config.output_config.excel_enabled = self.excel_checkbox.isChecked()
        self.config.output_config.csv_enabled = self.csv_checkbox.isChecked()
        self.config.output_config.powerpoint_enabled = self.powerpoint_checkbox.isChecked()
        self.config.output_config.hdf5_writeback_enabled = self.hdf5_checkbox.isChecked()
        self.config.output_config.output_directory = self.output_dir_edit.text()
    
    def _populate_ui_from_config(self):
        """Populate UI controls from configuration object."""
        # Data Source tab
        if self.config.source_type == "hdf5":
            self.hdf5_radio.setChecked(True)
            self.csv_radio.setChecked(False)
        else:
            self.csv_radio.setChecked(True)
            self.hdf5_radio.setChecked(False)

        # Update files display
        if self.config.source_files:
            self.files_text.setText("\n".join(self.config.source_files))

        # Update channels display
        if self.config.selected_channels:
            channel_text = "\n".join([f"{flight}/{channel}" for flight, channel in self.config.selected_channels])
            self.channels_text.setText(channel_text)
            self.selected_channels = self.config.selected_channels

        # Events tab
        self.full_duration_checkbox.setChecked(self.config.process_full_duration)
        self.events_table.setRowCount(0)  # Clear existing rows
        for event in self.config.events:
            self._add_event_row(event.name, event.start_time, event.end_time, event.description)

        # PSD Parameters tab
        method_index = self.psd_method_combo.findText(self.config.psd_config.method)
        if method_index >= 0:
            self.psd_method_combo.setCurrentIndex(method_index)

        window_index = self.window_combo.findText(self.config.psd_config.window)
        if window_index >= 0:
            self.window_combo.setCurrentIndex(window_index)

        self.overlap_spin.setValue(int(self.config.psd_config.overlap_percent))
        self.df_spin.setValue(self.config.psd_config.desired_df)
        self.efficient_fft_checkbox.setChecked(self.config.psd_config.use_efficient_fft)
        self.freq_min_spin.setValue(self.config.psd_config.freq_min)
        self.freq_max_spin.setValue(self.config.psd_config.freq_max)

        spacing_index = self.freq_spacing_combo.findText(self.config.psd_config.frequency_spacing)
        if spacing_index >= 0:
            self.freq_spacing_combo.setCurrentIndex(spacing_index)

        self.remove_mean_checkbox.setChecked(self.config.psd_config.remove_running_mean)

        # Filter tab
        self.filter_enabled_checkbox.setChecked(self.config.filter_config.enabled)

        filter_type_index = self.filter_type_combo.findText(self.config.filter_config.filter_type)
        if filter_type_index >= 0:
            self.filter_type_combo.setCurrentIndex(filter_type_index)

        filter_design_index = self.filter_design_combo.findText(self.config.filter_config.filter_design)
        if filter_design_index >= 0:
            self.filter_design_combo.setCurrentIndex(filter_design_index)

        self.filter_order_spin.setValue(self.config.filter_config.filter_order)
        # Handle None values for cutoff frequencies
        if self.config.filter_config.cutoff_low is not None:
            self.cutoff_low_spin.setValue(self.config.filter_config.cutoff_low)
        if self.config.filter_config.cutoff_high is not None:
            self.cutoff_high_spin.setValue(self.config.filter_config.cutoff_high)

        # Spectrogram tab
        self.spectrogram_enabled_checkbox.setChecked(self.config.spectrogram_config.enabled)
        self.spec_df_spin.setValue(self.config.spectrogram_config.desired_df)
        self.spec_overlap_spin.setValue(int(self.config.spectrogram_config.overlap_percent))
        self.spec_snr_spin.setValue(int(self.config.spectrogram_config.snr_threshold))

        colormap_index = self.colormap_combo.findText(self.config.spectrogram_config.colormap)
        if colormap_index >= 0:
            self.colormap_combo.setCurrentIndex(colormap_index)

        # Display tab
        self.psd_auto_scale_checkbox.setChecked(self.config.display_config.psd_auto_scale)
        if self.config.display_config.psd_x_axis_min is not None:
            self.psd_x_min_spin.setValue(self.config.display_config.psd_x_axis_min)
        if self.config.display_config.psd_x_axis_max is not None:
            self.psd_x_max_spin.setValue(self.config.display_config.psd_x_axis_max)
        if self.config.display_config.psd_y_axis_min is not None:
            self.psd_y_min_spin.setValue(self.config.display_config.psd_y_axis_min)
        if self.config.display_config.psd_y_axis_max is not None:
            self.psd_y_max_spin.setValue(self.config.display_config.psd_y_axis_max)
        self.psd_show_legend_checkbox.setChecked(self.config.display_config.psd_show_legend)
        self.psd_show_grid_checkbox.setChecked(self.config.display_config.psd_show_grid)

        # Output tab
        self.excel_checkbox.setChecked(self.config.output_config.excel_enabled)
        self.csv_checkbox.setChecked(self.config.output_config.csv_enabled)
        self.powerpoint_checkbox.setChecked(self.config.output_config.powerpoint_enabled)
        self.hdf5_checkbox.setChecked(self.config.output_config.hdf5_writeback_enabled)
        self.output_dir_edit.setText(self.config.output_config.output_directory or "")

    def _add_event_row(self, name: str, start_time: float, end_time: float, description: str = ""):
        """Helper method to add an event row to the table."""
        row = self.events_table.rowCount()
        self.events_table.insertRow(row)
        self.events_table.setItem(row, 0, QTableWidgetItem(name))
        self.events_table.setItem(row, 1, QTableWidgetItem(str(start_time)))
        self.events_table.setItem(row, 2, QTableWidgetItem(str(end_time)))
        self.events_table.setItem(row, 3, QTableWidgetItem(description))
    
    def _start_batch_processing(self):
        """Start batch processing in worker thread."""
        # Disable UI during processing
        self._set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Processing...")
        self.processing_log = []

        # Show cancel button
        self.cancel_btn.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.run_batch_btn.setEnabled(False)

        # Create and start worker
        self.batch_worker = BatchWorker(self.config)
        self.batch_worker.progress_updated.connect(self._on_progress_updated)
        self.batch_worker.processing_complete.connect(self._on_processing_complete)
        self.batch_worker.processing_failed.connect(self._on_processing_failed)
        self.batch_worker.log_message.connect(self._on_log_message)
        self.batch_worker.start()

        logger.info("Batch processing started")

    def _on_cancel_batch(self):
        """Handle cancel button click."""
        if self.batch_worker and self.batch_worker.isRunning():
            reply = show_question(
                self,
                "Cancel Processing",
                "Are you sure you want to cancel batch processing?\n\nThis may take a moment to stop."
            )
            if reply:
                self.status_label.setText("Cancelling...")
                self.cancel_btn.setEnabled(False)
                self.batch_worker.cancel()
                logger.info("Batch processing cancellation requested")
    
    def _on_progress_updated(self, percent: int, message: str):
        """Handle progress updates from worker."""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def _on_processing_complete(self, results: Dict):
        """Handle successful completion of batch processing."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Complete!")
        self._set_ui_enabled(True)

        # Hide cancel button
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(False)
        self.run_batch_btn.setEnabled(True)

        # Show completion message
        log_text = "\n".join(self.processing_log[-10:])  # Last 10 log messages
        show_information(
            self,
            "Batch Processing Complete",
            f"Batch processing completed successfully!\n\nOutput directory:\n{self.config.output_config.output_directory}\n\nRecent log:\n{log_text}"
        )

        logger.info("Batch processing completed successfully")
    
    def _on_processing_failed(self, error_message: str):
        """Handle batch processing failure."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Failed")
        self._set_ui_enabled(True)

        # Hide cancel button
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(False)
        self.run_batch_btn.setEnabled(True)

        show_critical(self, "Batch Processing Failed", error_message)
        logger.error(f"Batch processing failed: {error_message}")
    
    def _on_log_message(self, message: str):
        """Handle log messages from worker."""
        self.processing_log.append(message)
        logger.info(f"Batch: {message}")
    
    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable UI controls."""
        self.tab_widget.setEnabled(enabled)
        self.load_config_btn.setEnabled(enabled)
        self.save_config_btn.setEnabled(enabled)
        self.run_batch_btn.setEnabled(enabled)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = BatchProcessorWindow()
    window.show()
    sys.exit(app.exec())
