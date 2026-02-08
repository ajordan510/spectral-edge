"""
Batch Processor Setup GUI

This module provides a comprehensive GUI for setting up and running batch PSD processing.
Integrates with the Enhanced Flight Navigator for channel selection from HDF5 files.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import sys
import math
from pathlib import Path
from typing import List, Dict, Optional
import logging
import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QGroupBox, QCheckBox, QDoubleSpinBox, QSpinBox, QComboBox,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QToolButton, QButtonGroup, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QDoubleValidator, QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath


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
        self._create_statistics_tab()
        self._create_display_tab()
        self._create_output_tab()

        # Apply initial PowerPoint/spectrogram state
        self._update_spectrogram_controls()
        
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

        # DXD option (DEWESoft)
        dxd_layout = QHBoxLayout()
        self.dxd_radio = QCheckBox("DXD File(s) (DEWESoft)")
        self.select_dxd_btn = QPushButton("Select DXD Files")
        self.select_dxd_btn.setToolTip("Load DEWESoft DXD/DXZ data files")
        dxd_layout.addWidget(self.dxd_radio)
        dxd_layout.addWidget(self.select_dxd_btn)
        dxd_layout.addStretch()
        source_layout.addLayout(dxd_layout)

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
        self.psd_method_combo.setCurrentText("maximax")
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
        self.df_spin.setValue(5.0)
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
        self.freq_spacing_combo.addItem("Constant Bandwidth", "constant_bandwidth")
        self.freq_spacing_combo.addItem("1/36 Octave", "1/36")
        self.freq_spacing_combo.addItem("1/24 Octave", "1/24")
        self.freq_spacing_combo.addItem("1/12 Octave", "1/12")
        self.freq_spacing_combo.addItem("1/6 Octave", "1/6")
        self.freq_spacing_combo.addItem("1/3 Octave", "1/3")
        freq_row3.addWidget(QLabel("Frequency Spacing:"))
        freq_row3.addWidget(self.freq_spacing_combo)
        freq_row3.addStretch()
        freq_layout.addLayout(freq_row3)
        
        freq_group.setLayout(freq_layout)
        layout.addWidget(freq_group)
        
        # Mean removal with configurable window
        mean_group = QGroupBox("Running Mean Removal")
        mean_layout = QHBoxLayout()

        self.remove_mean_checkbox = QCheckBox("Remove Running Mean")
        self.remove_mean_checkbox.setChecked(True)
        mean_layout.addWidget(self.remove_mean_checkbox)

        mean_layout.addWidget(QLabel("Window:"))
        self.running_mean_window_spin = QDoubleSpinBox()
        self.running_mean_window_spin.setRange(0.1, 10.0)
        self.running_mean_window_spin.setValue(1.0)
        self.running_mean_window_spin.setSuffix(" s")
        self.running_mean_window_spin.setDecimals(1)
        self.running_mean_window_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        mean_layout.addWidget(self.running_mean_window_spin)
        mean_layout.addStretch()

        mean_group.setLayout(mean_layout)
        layout.addWidget(mean_group)
        
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
        
        # Spectrogram generation is controlled by the PowerPoint layout selection
        self.spectrogram_info_label = QLabel(
            "Spectrograms are generated when the PowerPoint layout includes them."
        )
        self.spectrogram_info_label.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        self.spectrogram_info_label.setWordWrap(True)
        layout.addWidget(self.spectrogram_info_label)
        
        # Spectrogram settings
        spec_group = QGroupBox("Spectrogram Settings")
        spec_layout = QVBoxLayout()
        
        # Parameters
        param_row1 = QHBoxLayout()
        self.spec_df_spin = QDoubleSpinBox()
        self.spec_df_spin.setRange(0.01, 100.0)
        self.spec_df_spin.setValue(2.0)
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
        self.spec_snr_spin.setValue(50)
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

    def _create_statistics_tab(self):
        """Create the statistics configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QLabel("Statistics are calculated for PowerPoint output when enabled.")
        info.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # PDF options
        pdf_group = QGroupBox("PDF Options")
        pdf_layout = QVBoxLayout()

        bins_row = QHBoxLayout()
        bins_row.addWidget(QLabel("Number of Bins:"))
        self.stats_bins_spin = QSpinBox()
        self.stats_bins_spin.setRange(10, 1000)
        self.stats_bins_spin.setValue(50)
        bins_row.addWidget(self.stats_bins_spin)
        bins_row.addStretch()
        pdf_layout.addLayout(bins_row)

        overlays_label = QLabel("Distribution Overlays:")
        overlays_label.setStyleSheet("color: #e0e0e0;")
        pdf_layout.addWidget(overlays_label)

        self.stats_normal_checkbox = QCheckBox("Normal")
        self.stats_normal_checkbox.setChecked(True)
        pdf_layout.addWidget(self.stats_normal_checkbox)

        self.stats_rayleigh_checkbox = QCheckBox("Rayleigh")
        self.stats_rayleigh_checkbox.setChecked(False)
        pdf_layout.addWidget(self.stats_rayleigh_checkbox)

        self.stats_uniform_checkbox = QCheckBox("Uniform")
        self.stats_uniform_checkbox.setChecked(False)
        pdf_layout.addWidget(self.stats_uniform_checkbox)

        pdf_group.setLayout(pdf_layout)
        layout.addWidget(pdf_group)

        # Running statistics options
        running_group = QGroupBox("Running Statistics")
        running_layout = QVBoxLayout()

        window_row = QHBoxLayout()
        window_row.addWidget(QLabel("Window Size (s):"))
        self.stats_window_spin = QDoubleSpinBox()
        self.stats_window_spin.setRange(0.1, 20.0)
        self.stats_window_spin.setValue(1.0)
        self.stats_window_spin.setSingleStep(0.1)
        window_row.addWidget(self.stats_window_spin)
        window_row.addStretch()
        running_layout.addLayout(window_row)

        running_layout.addWidget(QLabel("Display:"))
        self.stats_show_mean_checkbox = QCheckBox("Mean")
        self.stats_show_mean_checkbox.setChecked(True)
        running_layout.addWidget(self.stats_show_mean_checkbox)

        self.stats_show_std_checkbox = QCheckBox("Standard Deviation")
        self.stats_show_std_checkbox.setChecked(True)
        running_layout.addWidget(self.stats_show_std_checkbox)

        self.stats_show_skew_checkbox = QCheckBox("Skewness")
        self.stats_show_skew_checkbox.setChecked(True)
        running_layout.addWidget(self.stats_show_skew_checkbox)

        self.stats_show_kurt_checkbox = QCheckBox("Kurtosis")
        self.stats_show_kurt_checkbox.setChecked(True)
        running_layout.addWidget(self.stats_show_kurt_checkbox)

        running_group.setLayout(running_layout)
        layout.addWidget(running_group)

        # Plot settings
        plot_group = QGroupBox("Plot Settings")
        plot_layout = QHBoxLayout()
        max_points_label = QLabel("Running Stats Plot Point Limit:")
        max_points_label.setToolTip(
            "Caps plotted samples for running-stat curves to keep report generation responsive; "
            "does not change PSD calculations."
        )
        plot_layout.addWidget(max_points_label)
        self.stats_max_points_spin = QSpinBox()
        self.stats_max_points_spin.setRange(100, 20000)
        self.stats_max_points_spin.setValue(5000)
        self.stats_max_points_spin.setToolTip(
            "Caps plotted samples for running-stat curves to keep report generation responsive; "
            "does not change PSD calculations."
        )
        plot_layout.addWidget(self.stats_max_points_spin)
        plot_layout.addStretch()
        plot_group.setLayout(plot_layout)
        layout.addWidget(plot_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Statistics")
    
    def _create_display_tab(self):
        """Create the display settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # PSD plot settings
        psd_group = QGroupBox("PSD Plot Display Settings")
        psd_layout = QVBoxLayout()

        self.psd_auto_scale_checkbox = QCheckBox("Auto-scale axes")
        self.psd_auto_scale_checkbox.stateChanged.connect(self._on_psd_auto_scale_changed)
        psd_layout.addWidget(self.psd_auto_scale_checkbox)

        # X-axis limits
        x_axis_row = QHBoxLayout()
        self.psd_x_label = QLabel("X-axis (Frequency):")
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
        self.psd_x_to_label = QLabel("to")
        x_axis_row.addWidget(self.psd_x_label)
        x_axis_row.addWidget(self.psd_x_min_spin)
        x_axis_row.addWidget(self.psd_x_to_label)
        x_axis_row.addWidget(self.psd_x_max_spin)
        x_axis_row.addStretch()
        psd_layout.addLayout(x_axis_row)

        # Y-axis limits (scientific notation for PSD values)
        y_axis_row = QHBoxLayout()
        self.psd_y_label = QLabel("Y-axis (PSD):")
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
        self.psd_y_to_label = QLabel("to")
        y_axis_row.addWidget(self.psd_y_label)
        y_axis_row.addWidget(self.psd_y_min_spin)
        y_axis_row.addWidget(self.psd_y_to_label)
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

        # Spectrogram display settings
        spec_group = QGroupBox("Spectrogram Display Settings")
        spec_layout = QVBoxLayout()

        self.spec_auto_scale_checkbox = QCheckBox("Auto-scale axes")
        self.spec_auto_scale_checkbox.setChecked(True)
        self.spec_auto_scale_checkbox.stateChanged.connect(self._on_spec_auto_scale_changed)
        spec_layout.addWidget(self.spec_auto_scale_checkbox)

        # Frequency limits
        spec_freq_row = QHBoxLayout()
        self.spec_freq_label = QLabel("Frequency Range:")
        self.spec_freq_min_spin = QDoubleSpinBox()
        self.spec_freq_min_spin.setRange(0.1, 100000.0)
        self.spec_freq_min_spin.setValue(20.0)
        self.spec_freq_min_spin.setSuffix(" Hz")
        self.spec_freq_min_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.spec_freq_min_spin.setEnabled(False)
        self.spec_freq_max_spin = QDoubleSpinBox()
        self.spec_freq_max_spin.setRange(1.0, 100000.0)
        self.spec_freq_max_spin.setValue(2000.0)
        self.spec_freq_max_spin.setSuffix(" Hz")
        self.spec_freq_max_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.spec_freq_max_spin.setEnabled(False)
        self.spec_freq_to_label = QLabel("to")
        spec_freq_row.addWidget(self.spec_freq_label)
        spec_freq_row.addWidget(self.spec_freq_min_spin)
        spec_freq_row.addWidget(self.spec_freq_to_label)
        spec_freq_row.addWidget(self.spec_freq_max_spin)
        spec_freq_row.addStretch()
        spec_layout.addLayout(spec_freq_row)

        # Time limits
        spec_time_row = QHBoxLayout()
        self.spec_time_label = QLabel("Time Range:")
        self.spec_time_min_spin = QDoubleSpinBox()
        self.spec_time_min_spin.setRange(0.0, 100000.0)
        self.spec_time_min_spin.setValue(0.0)
        self.spec_time_min_spin.setSuffix(" s")
        self.spec_time_min_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.spec_time_min_spin.setEnabled(False)
        self.spec_time_max_spin = QDoubleSpinBox()
        self.spec_time_max_spin.setRange(0.0, 100000.0)
        self.spec_time_max_spin.setValue(10.0)
        self.spec_time_max_spin.setSuffix(" s")
        self.spec_time_max_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.spec_time_max_spin.setEnabled(False)
        self.spec_time_to_label = QLabel("to")
        spec_time_row.addWidget(self.spec_time_label)
        spec_time_row.addWidget(self.spec_time_min_spin)
        spec_time_row.addWidget(self.spec_time_to_label)
        spec_time_row.addWidget(self.spec_time_max_spin)
        spec_time_row.addStretch()
        spec_layout.addLayout(spec_time_row)

        spec_group.setLayout(spec_layout)
        layout.addWidget(spec_group)

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

        # PowerPoint report options
        self.ppt_group = QGroupBox("PowerPoint Report Options")
        ppt_layout = QVBoxLayout()

        layout_label = QLabel("Layout:")
        ppt_layout.addWidget(layout_label)

        self.ppt_layout_buttons = QButtonGroup(self)
        self.ppt_layout_buttons.setExclusive(True)

        self.ppt_layout_labels = {
            "time_psd_spec_one_slide": "Time + PSD + Spec",
            "all_plots_individual": "All Plots\nIndividual",
            "psd_spec_side_by_side": "PSD + Spec\nSide by Side",
            "psd_only": "PSD Only",
            "spectrogram_only": "Spectrogram Only",
            "time_history_only": "Time History Only"
        }

        layout_grid = QGridLayout()
        layout_grid.setHorizontalSpacing(12)
        layout_grid.setVerticalSpacing(12)

        layout_options = [
            ("time_psd_spec_one_slide", "Time + PSD + Spectrogram (one slide)"),
            ("all_plots_individual", "All plots on individual slides"),
            ("psd_spec_side_by_side", "PSD + Spectrogram (side by side)"),
            ("psd_only", "PSD only"),
            ("spectrogram_only", "Spectrogram only"),
            ("time_history_only", "Time history only")
        ]

        for idx, (layout_value, tooltip) in enumerate(layout_options):
            label = self.ppt_layout_labels[layout_value]
            button = self._create_ppt_layout_button(layout_value, label, tooltip)
            self.ppt_layout_buttons.addButton(button)
            row = idx // 3
            col = idx % 3
            layout_grid.addWidget(button, row, col)

        ppt_layout.addLayout(layout_grid)
        self._set_selected_ppt_layout(self.config.powerpoint_config.layout)

        self.ppt_include_parameters_checkbox = QCheckBox("Include calculation parameters")
        self.ppt_include_parameters_checkbox.setChecked(True)
        ppt_layout.addWidget(self.ppt_include_parameters_checkbox)

        self.ppt_include_statistics_checkbox = QCheckBox("Include statistics slides")
        self.ppt_include_statistics_checkbox.setChecked(False)
        ppt_layout.addWidget(self.ppt_include_statistics_checkbox)

        self.ppt_include_rms_table_checkbox = QCheckBox("Include RMS summary table")
        self.ppt_include_rms_table_checkbox.setChecked(False)
        ppt_layout.addWidget(self.ppt_include_rms_table_checkbox)

        self.ppt_include_3sigma_columns_checkbox = QCheckBox("Include 3-sigma columns in RMS table")
        self.ppt_include_3sigma_columns_checkbox.setChecked(False)
        self.ppt_include_3sigma_columns_checkbox.setEnabled(False)
        ppt_layout.addWidget(self.ppt_include_3sigma_columns_checkbox)

        self.ppt_group.setLayout(ppt_layout)
        layout.addWidget(self.ppt_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Output")
    
    def _connect_signals(self):
        """Connect signals to slots."""
        # File selection
        self.select_hdf5_btn.clicked.connect(self._on_select_hdf5)
        self.select_csv_btn.clicked.connect(self._on_select_csv)
        self.select_dxd_btn.clicked.connect(self._on_select_dxd)
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

        # PowerPoint layout options
        if hasattr(self, "ppt_layout_buttons"):
            self.ppt_layout_buttons.buttonClicked.connect(self._on_ppt_layout_changed)
        self.powerpoint_checkbox.stateChanged.connect(self._on_powerpoint_enabled_changed)
        self.ppt_include_rms_table_checkbox.toggled.connect(self._on_rms_table_toggled)

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
            QToolButton {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                border-radius: 6px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #374151;
            }
            QToolButton:checked {
                border: 2px solid #60a5fa;
                background-color: #1f2937;
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
            self.dxd_radio.setChecked(False)
            if not self.output_dir_edit.text().strip():
                default_dir = str(Path(files[0]).parent)
                self.output_dir_edit.setText(default_dir)
                self.config.output_config.output_directory = default_dir
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
            self.dxd_radio.setChecked(False)
            if not self.output_dir_edit.text().strip():
                default_dir = str(Path(files[0]).parent)
                self.output_dir_edit.setText(default_dir)
                self.config.output_config.output_directory = default_dir
            logger.info(f"Selected {len(files)} CSV file(s)")

    def _on_select_dxd(self):
        """Handle DXD file selection."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select DEWESoft Files",
            "",
            "DEWESoft Files (*.dxd *.dxz *.d7d *.d7z);;All Files (*)"
        )

        if files:
            self.config.source_type = "dxd"
            self.config.source_files = files
            self.files_text.setText("\n".join(files))
            self.dxd_radio.setChecked(True)
            self.hdf5_radio.setChecked(False)
            self.csv_radio.setChecked(False)
            if not self.output_dir_edit.text().strip():
                default_dir = str(Path(files[0]).parent)
                self.output_dir_edit.setText(default_dir)
                self.config.output_config.output_directory = default_dir
            logger.info(f"Selected {len(files)} DXD file(s)")

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

    def _build_layout_icon(self, layout_value: str) -> QIcon:
        """Create a visual mockup icon for a PowerPoint layout option."""
        width, height = 140, 95
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#ffffff"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#1f2937"))
        pen.setWidth(2)
        painter.setPen(pen)

        # Draw slide border
        painter.drawRect(2, 2, width - 4, height - 4)

        # Helper for panels
        def panel(x, y, w, h, fill=None):
            if fill:
                painter.fillRect(x, y, w, h, QColor(fill))
            painter.drawRect(x, y, w, h)

        def draw_squiggle(x, y, w, h):
            path = QPainterPath()
            mid = y + h / 2
            amp = h * 0.25
            steps = 8
            path.moveTo(x, mid)
            for i in range(1, steps + 1):
                px = x + (w * i / steps)
                py = mid + amp * math.sin(i * 1.2)
                path.lineTo(px, py)
            painter.drawPath(path)

        def draw_time_wave(x, y, w, h):
            path = QPainterPath()
            mid = y + h / 2
            amp = h * 0.35
            steps = 10
            path.moveTo(x, mid)
            for i in range(1, steps + 1):
                px = x + (w * i / steps)
                py = mid + amp * math.sin(i * 1.6)
                path.lineTo(px, py)
            painter.drawPath(path)

        def draw_spec_shading(x, y, w, h):
            shades = ["#d1d5db", "#e5e7eb", "#cbd5e1", "#e5e7eb"]
            stripe_w = max(1, int(w / len(shades)))
            for i, shade in enumerate(shades):
                painter.fillRect(x + i * stripe_w, y, stripe_w, h, QColor(shade))
            painter.drawRect(x, y, w, h)

        if layout_value == "time_psd_spec_one_slide":
            panel(8, 10, width - 16, 28, "#f3f4f6")
            draw_time_wave(14, 14, width - 28, 20)
            panel(8, 46, (width - 20) // 2, 38, "#f9fafb")
            draw_squiggle(12, 54, (width - 20) // 2 - 8, 22)
            draw_spec_shading(12 + (width - 20) // 2, 46, (width - 20) // 2, 38)
        elif layout_value == "all_plots_individual":
            # mock three stacked mini slides with depth
            panel(18, 18, width - 36, 18, "#f9fafb")
            panel(14, 14, width - 36, 18, "#f3f4f6")
            panel(10, 10, width - 36, 18, "#f9fafb")
        elif layout_value == "psd_spec_side_by_side":
            panel(8, 14, (width - 20) // 2, height - 26, "#f3f4f6")
            draw_squiggle(12, 24, (width - 20) // 2 - 8, height - 46)
            draw_spec_shading(12 + (width - 20) // 2, 14, (width - 20) // 2, height - 26)
        elif layout_value == "psd_only":
            panel(10, 18, width - 20, height - 32, "#f3f4f6")
            draw_squiggle(16, 26, width - 32, height - 48)
        elif layout_value == "spectrogram_only":
            draw_spec_shading(10, 18, width - 20, height - 32)
        elif layout_value == "time_history_only":
            panel(10, 18, width - 20, height - 32, "#f9fafb")
            draw_time_wave(16, 26, width - 32, height - 48)

        painter.end()
        return QIcon(pixmap)

    def _create_ppt_layout_button(self, layout_value: str, label: str, tooltip: str) -> QToolButton:
        """Create a checkable layout selection button with icon."""
        button = QToolButton()
        button.setCheckable(True)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setIcon(self._build_layout_icon(layout_value))
        button.setIconSize(QSize(120, 80))
        button.setText(label)
        button.setToolTip(tooltip)
        button.setProperty("layout_value", layout_value)
        button.setAutoRaise(False)
        return button

    def _get_selected_ppt_layout(self) -> str:
        """Return currently selected layout value."""
        if not hasattr(self, "ppt_layout_buttons"):
            return self.config.powerpoint_config.layout
        button = self.ppt_layout_buttons.checkedButton()
        if button is None:
            return self.config.powerpoint_config.layout
        return button.property("layout_value")

    def _set_selected_ppt_layout(self, layout_value: str) -> None:
        """Select the layout button matching the provided value."""
        if not hasattr(self, "ppt_layout_buttons"):
            return
        for button in self.ppt_layout_buttons.buttons():
            if button.property("layout_value") == layout_value:
                button.setChecked(True)
                return
        # Default to first button if not found
        buttons = self.ppt_layout_buttons.buttons()
        if buttons:
            buttons[0].setChecked(True)

    def _get_layout_label(self, layout_value: str) -> str:
        if not hasattr(self, "ppt_layout_labels"):
            return layout_value
        label = self.ppt_layout_labels.get(layout_value, layout_value)
        return label.replace("\n", " ")

    def _layout_includes_spectrogram(self, layout_value: str) -> bool:
        return layout_value in {
            "time_psd_spec_one_slide",
            "all_plots_individual",
            "psd_spec_side_by_side",
            "spectrogram_only"
        }

    def _update_spectrogram_controls(self):
        """Enable/disable spectrogram controls based on layout selection."""
        layout_value = self._get_selected_ppt_layout()
        include_spec = self.powerpoint_checkbox.isChecked() and self._layout_includes_spectrogram(layout_value)

        # Update config and UI controls
        self.config.spectrogram_config.enabled = include_spec

        for widget in [
            self.spec_df_spin,
            self.spec_overlap_spin,
            self.spec_snr_spin,
            self.colormap_combo,
            self.spec_auto_scale_checkbox,
            self.spec_freq_min_spin,
            self.spec_freq_max_spin,
            self.spec_time_min_spin,
            self.spec_time_max_spin
        ]:
            widget.setEnabled(include_spec)

        # Re-apply auto-scale logic for manual limits
        self._on_spec_auto_scale_changed(
            Qt.CheckState.Checked.value if self.spec_auto_scale_checkbox.isChecked()
            else Qt.CheckState.Unchecked.value
        )

    def _on_ppt_layout_changed(self):
        """Handle PowerPoint layout change."""
        self._update_spectrogram_controls()

    def _on_rms_table_toggled(self, checked: bool):
        """Enable/disable 3-sigma columns option based on RMS table selection."""
        self.ppt_include_3sigma_columns_checkbox.setEnabled(checked)
        if not checked:
            self.ppt_include_3sigma_columns_checkbox.setChecked(False)

    def _on_powerpoint_enabled_changed(self):
        """Enable/disable PowerPoint options when output is toggled."""
        is_enabled = self.powerpoint_checkbox.isChecked()
        self.ppt_group.setEnabled(is_enabled)
        self._update_spectrogram_controls()
    
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
                is_valid, error_msg = self._validate_events_table()
                if not is_valid:
                    show_warning(self, "Configuration Issues", f"Please fix the following issues:\n\n{error_msg}")
                    logger.warning(f"Pre-validation failed: {error_msg}")
                    return

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

            # Early validation before expensive operations
            is_valid, error_msg = self._validate_configuration_before_run()
            if not is_valid:
                show_warning(self, "Configuration Issues", f"Please fix the following issues:\n\n{error_msg}")
                logger.warning(f"Pre-validation failed: {error_msg}")
                return

            # Validate full configuration
            self.config.validate()

            # Show pre-processing summary and get confirmation
            if not self._show_pre_processing_summary():
                logger.info("Batch processing cancelled by user at summary")
                return

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
        self.config.psd_config.frequency_spacing = self.freq_spacing_combo.currentData()
        self.config.psd_config.remove_running_mean = self.remove_mean_checkbox.isChecked()
        self.config.psd_config.running_mean_window = self.running_mean_window_spin.value()
        
        # Filter config
        self.config.filter_config.enabled = self.filter_enabled_checkbox.isChecked()
        self.config.filter_config.filter_type = self.filter_type_combo.currentText()
        self.config.filter_config.filter_design = self.filter_design_combo.currentText()
        self.config.filter_config.filter_order = self.filter_order_spin.value()
        self.config.filter_config.cutoff_low = self.cutoff_low_spin.value()
        self.config.filter_config.cutoff_high = self.cutoff_high_spin.value()
        
        # Spectrogram config
        self.config.spectrogram_config.enabled = (
            self.powerpoint_checkbox.isChecked()
            and self._layout_includes_spectrogram(self._get_selected_ppt_layout())
        )
        self.config.spectrogram_config.desired_df = self.spec_df_spin.value()
        self.config.spectrogram_config.overlap_percent = float(self.spec_overlap_spin.value())
        self.config.spectrogram_config.snr_threshold = float(self.spec_snr_spin.value())
        self.config.spectrogram_config.colormap = self.colormap_combo.currentText()
        
        # Display config - PSD
        self.config.display_config.psd_auto_scale = self.psd_auto_scale_checkbox.isChecked()
        self.config.display_config.psd_x_axis_min = self.psd_x_min_spin.value()
        self.config.display_config.psd_x_axis_max = self.psd_x_max_spin.value()
        self.config.display_config.psd_y_axis_min = self.psd_y_min_spin.value()
        self.config.display_config.psd_y_axis_max = self.psd_y_max_spin.value()
        self.config.display_config.psd_show_legend = self.psd_show_legend_checkbox.isChecked()
        self.config.display_config.psd_show_grid = self.psd_show_grid_checkbox.isChecked()

        # Display config - Spectrogram
        self.config.display_config.spectrogram_auto_scale = self.spec_auto_scale_checkbox.isChecked()
        self.config.display_config.spectrogram_freq_min = self.spec_freq_min_spin.value()
        self.config.display_config.spectrogram_freq_max = self.spec_freq_max_spin.value()
        self.config.display_config.spectrogram_time_min = self.spec_time_min_spin.value()
        self.config.display_config.spectrogram_time_max = self.spec_time_max_spin.value()
        
        # Output config
        self.config.output_config.excel_enabled = self.excel_checkbox.isChecked()
        self.config.output_config.csv_enabled = self.csv_checkbox.isChecked()
        self.config.output_config.powerpoint_enabled = self.powerpoint_checkbox.isChecked()
        self.config.output_config.hdf5_writeback_enabled = self.hdf5_checkbox.isChecked()
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir and self.config.source_files:
            output_dir = str(Path(self.config.source_files[0]).parent)
            self.output_dir_edit.setText(output_dir)
        self.config.output_config.output_directory = output_dir

        # PowerPoint config
        self.config.powerpoint_config.layout = self._get_selected_ppt_layout()
        self.config.powerpoint_config.include_parameters = self.ppt_include_parameters_checkbox.isChecked()
        self.config.powerpoint_config.include_statistics = self.ppt_include_statistics_checkbox.isChecked()
        self.config.powerpoint_config.include_rms_table = self.ppt_include_rms_table_checkbox.isChecked()
        self.config.powerpoint_config.include_3sigma_columns = self.ppt_include_3sigma_columns_checkbox.isChecked()

        # Statistics config
        self.config.statistics_config.enabled = self.ppt_include_statistics_checkbox.isChecked()
        self.config.statistics_config.pdf_bins = self.stats_bins_spin.value()
        self.config.statistics_config.running_window_seconds = self.stats_window_spin.value()
        self.config.statistics_config.show_mean = self.stats_show_mean_checkbox.isChecked()
        self.config.statistics_config.show_std = self.stats_show_std_checkbox.isChecked()
        self.config.statistics_config.show_skewness = self.stats_show_skew_checkbox.isChecked()
        self.config.statistics_config.show_kurtosis = self.stats_show_kurt_checkbox.isChecked()
        self.config.statistics_config.show_normal = self.stats_normal_checkbox.isChecked()
        self.config.statistics_config.show_rayleigh = self.stats_rayleigh_checkbox.isChecked()
        self.config.statistics_config.show_uniform = self.stats_uniform_checkbox.isChecked()
        self.config.statistics_config.max_plot_points = self.stats_max_points_spin.value()
    
    def _populate_ui_from_config(self):
        """Populate UI controls from configuration object."""
        # Data Source tab
        self.hdf5_radio.setChecked(False)
        self.csv_radio.setChecked(False)
        self.dxd_radio.setChecked(False)

        if self.config.source_type == "hdf5":
            self.hdf5_radio.setChecked(True)
        elif self.config.source_type == "csv":
            self.csv_radio.setChecked(True)
        elif self.config.source_type == "dxd":
            self.dxd_radio.setChecked(True)

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

        spacing_index = self.freq_spacing_combo.findData(self.config.psd_config.frequency_spacing)
        if spacing_index >= 0:
            self.freq_spacing_combo.setCurrentIndex(spacing_index)

        self.remove_mean_checkbox.setChecked(self.config.psd_config.remove_running_mean)
        self.running_mean_window_spin.setValue(self.config.psd_config.running_mean_window)

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
        self.spec_df_spin.setValue(self.config.spectrogram_config.desired_df)
        self.spec_overlap_spin.setValue(int(self.config.spectrogram_config.overlap_percent))
        self.spec_snr_spin.setValue(int(self.config.spectrogram_config.snr_threshold))

        colormap_index = self.colormap_combo.findText(self.config.spectrogram_config.colormap)
        if colormap_index >= 0:
            self.colormap_combo.setCurrentIndex(colormap_index)

        # Display tab - PSD settings
        self.psd_auto_scale_checkbox.setChecked(self.config.display_config.psd_auto_scale)
        # Trigger the auto-scale handler to set initial enabled states
        self._on_psd_auto_scale_changed(
            Qt.CheckState.Checked.value if self.config.display_config.psd_auto_scale else Qt.CheckState.Unchecked.value
        )
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

        # Display tab - Spectrogram settings
        self.spec_auto_scale_checkbox.setChecked(self.config.display_config.spectrogram_auto_scale)
        # Trigger the auto-scale handler to set initial enabled states
        self._on_spec_auto_scale_changed(
            Qt.CheckState.Checked.value if self.config.display_config.spectrogram_auto_scale else Qt.CheckState.Unchecked.value
        )
        if self.config.display_config.spectrogram_freq_min is not None:
            self.spec_freq_min_spin.setValue(self.config.display_config.spectrogram_freq_min)
        if self.config.display_config.spectrogram_freq_max is not None:
            self.spec_freq_max_spin.setValue(self.config.display_config.spectrogram_freq_max)
        if self.config.display_config.spectrogram_time_min is not None:
            self.spec_time_min_spin.setValue(self.config.display_config.spectrogram_time_min)
        if self.config.display_config.spectrogram_time_max is not None:
            self.spec_time_max_spin.setValue(self.config.display_config.spectrogram_time_max)

        # Output tab
        self.excel_checkbox.setChecked(self.config.output_config.excel_enabled)
        self.csv_checkbox.setChecked(self.config.output_config.csv_enabled)
        self.powerpoint_checkbox.setChecked(self.config.output_config.powerpoint_enabled)
        self.ppt_group.setEnabled(self.powerpoint_checkbox.isChecked())

        # PowerPoint report options
        self._set_selected_ppt_layout(self.config.powerpoint_config.layout)
        self.ppt_include_parameters_checkbox.setChecked(self.config.powerpoint_config.include_parameters)
        self.ppt_include_statistics_checkbox.setChecked(self.config.powerpoint_config.include_statistics)
        self.ppt_include_rms_table_checkbox.setChecked(self.config.powerpoint_config.include_rms_table)
        self.ppt_include_3sigma_columns_checkbox.setChecked(
            self.config.powerpoint_config.include_3sigma_columns
        )
        self._on_rms_table_toggled(self.config.powerpoint_config.include_rms_table)

        # Statistics options
        self.stats_bins_spin.setValue(self.config.statistics_config.pdf_bins)
        self.stats_window_spin.setValue(self.config.statistics_config.running_window_seconds)
        self.stats_show_mean_checkbox.setChecked(self.config.statistics_config.show_mean)
        self.stats_show_std_checkbox.setChecked(self.config.statistics_config.show_std)
        self.stats_show_skew_checkbox.setChecked(self.config.statistics_config.show_skewness)
        self.stats_show_kurt_checkbox.setChecked(self.config.statistics_config.show_kurtosis)
        self.stats_normal_checkbox.setChecked(self.config.statistics_config.show_normal)
        self.stats_rayleigh_checkbox.setChecked(self.config.statistics_config.show_rayleigh)
        self.stats_uniform_checkbox.setChecked(self.config.statistics_config.show_uniform)
        self.stats_max_points_spin.setValue(self.config.statistics_config.max_plot_points)

        # Ensure spectrogram controls match layout
        self._update_spectrogram_controls()
        self.hdf5_checkbox.setChecked(self.config.output_config.hdf5_writeback_enabled)
        output_dir = self.config.output_config.output_directory
        if not output_dir and self.config.source_files:
            output_dir = str(Path(self.config.source_files[0]).parent)
            self.config.output_config.output_directory = output_dir
        self.output_dir_edit.setText(output_dir or "")

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

    def _on_psd_auto_scale_changed(self, state: int):
        """Handle PSD auto-scale checkbox state change."""
        is_auto = state == Qt.CheckState.Checked.value
        # Disable manual limit controls when auto-scale is enabled
        self.psd_x_min_spin.setEnabled(not is_auto)
        self.psd_x_max_spin.setEnabled(not is_auto)
        self.psd_y_min_spin.setEnabled(not is_auto)
        self.psd_y_max_spin.setEnabled(not is_auto)
        # Update label styling to indicate disabled state
        style = "color: #6b7280;" if is_auto else "color: #e0e0e0;"
        self.psd_x_label.setStyleSheet(style)
        self.psd_x_to_label.setStyleSheet(style)
        self.psd_y_label.setStyleSheet(style)
        self.psd_y_to_label.setStyleSheet(style)

    def _on_spec_auto_scale_changed(self, state: int):
        """Handle spectrogram auto-scale checkbox state change."""
        is_auto = state == Qt.CheckState.Checked.value
        spec_enabled = self.powerpoint_checkbox.isChecked() and self._layout_includes_spectrogram(
            self._get_selected_ppt_layout()
        )
        # Disable manual limit controls when auto-scale is enabled
        manual_enabled = (not is_auto) and spec_enabled
        self.spec_freq_min_spin.setEnabled(manual_enabled)
        self.spec_freq_max_spin.setEnabled(manual_enabled)
        self.spec_time_min_spin.setEnabled(manual_enabled)
        self.spec_time_max_spin.setEnabled(manual_enabled)
        # Update label styling to indicate disabled state
        style = "color: #6b7280;" if is_auto or not spec_enabled else "color: #e0e0e0;"
        self.spec_freq_label.setStyleSheet(style)
        self.spec_freq_to_label.setStyleSheet(style)
        self.spec_time_label.setStyleSheet(style)
        self.spec_time_to_label.setStyleSheet(style)

    def _validate_event_time(self, text: str) -> bool:
        """Validate that event time text is a valid positive number."""
        try:
            value = float(text)
            return value >= 0
        except (ValueError, TypeError):
            return False

    def _validate_configuration_before_run(self) -> tuple:
        """
        Validate configuration before running batch processing.

        Returns:
        --------
        tuple
            (is_valid: bool, error_message: str or None)
        """
        errors = []

        # Validate output directory exists
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            errors.append("Output directory is not specified")
        elif not Path(output_dir).exists():
            errors.append(f"Output directory does not exist: {output_dir}")
        elif not Path(output_dir).is_dir():
            errors.append(f"Output path is not a directory: {output_dir}")

        # Validate source files
        if not self.config.source_files:
            errors.append("No source files selected")

        # Validate channels for HDF5
        if self.config.source_type == "hdf5" and not self.selected_channels:
            errors.append("No channels selected for HDF5 processing")

        # Validate event times if events are defined
        events_valid, events_error = self._validate_events_table()
        if not events_valid:
            errors.append(events_error)

        # Validate spectrogram manual ranges at run time only
        if (
            self.config.spectrogram_config.enabled
            and not self.config.display_config.spectrogram_auto_scale
        ):
            fmin = self.config.display_config.spectrogram_freq_min
            fmax = self.config.display_config.spectrogram_freq_max
            tmin = self.config.display_config.spectrogram_time_min
            tmax = self.config.display_config.spectrogram_time_max
            if fmin is None or fmax is None or fmin >= fmax:
                errors.append("Spectrogram frequency limits are invalid (min must be less than max)")
            if tmin is None or tmax is None or tmin >= tmax:
                errors.append("Spectrogram time limits are invalid (min must be less than max)")

        if errors:
            return False, "\n".join(errors)
        return True, None

    def _validate_events_table(self) -> tuple:
        """Validate event table entries."""
        errors = []

        if not self.full_duration_checkbox.isChecked():
            for row in range(self.events_table.rowCount()):
                event_name = self.events_table.item(row, 0)
                start_item = self.events_table.item(row, 1)
                end_item = self.events_table.item(row, 2)

                if event_name and start_item and end_item:
                    name = event_name.text()
                    if not self._validate_event_time(start_item.text()):
                        errors.append(f"Event '{name}': Invalid start time")
                    if not self._validate_event_time(end_item.text()):
                        errors.append(f"Event '{name}': Invalid end time")
                    else:
                        try:
                            start = float(start_item.text())
                            end = float(end_item.text())
                            if start >= end:
                                errors.append(f"Event '{name}': Start time must be less than end time")
                        except ValueError:
                            pass  # Already caught above

            if self.events_table.rowCount() == 0:
                errors.append("No events defined and 'Process Full Duration' is unchecked")

        if errors:
            return False, "\n".join(errors)
        return True, None

    def _show_pre_processing_summary(self) -> bool:
        """
        Show pre-processing summary and get user confirmation.

        Returns:
        --------
        bool
            True if user confirms, False otherwise
        """
        # Build summary
        summary_lines = []

        # Source files
        num_files = len(self.config.source_files)
        summary_lines.append(f"Source Files: {num_files} {self.config.source_type.upper()} file(s)")

        # Channels
        num_channels = len(self.selected_channels)
        summary_lines.append(f"Channels: {num_channels} selected")

        # Events
        if self.full_duration_checkbox.isChecked():
            summary_lines.append("Events: Full duration processing")
        else:
            num_events = self.events_table.rowCount()
            summary_lines.append(f"Events: {num_events} defined event(s)")

        # Processing options
        options = []
        if self.config.filter_config.enabled:
            options.append("Filtering")
        if self.config.psd_config.remove_running_mean:
            options.append("Mean removal")
        if self.config.spectrogram_config.enabled:
            options.append("Spectrograms")
        summary_lines.append(f"Processing: {', '.join(options) if options else 'PSD only'}")
        summary_lines.append(f"Frequency Spacing: {self.config.psd_config.frequency_spacing}")

        # Output formats
        outputs = []
        if self.excel_checkbox.isChecked():
            outputs.append("Excel")
        if self.csv_checkbox.isChecked():
            outputs.append("CSV")
        if self.powerpoint_checkbox.isChecked():
            outputs.append("PowerPoint")
        if self.hdf5_checkbox.isChecked():
            outputs.append("HDF5")
        summary_lines.append(f"Outputs: {', '.join(outputs)}")
        if self.powerpoint_checkbox.isChecked():
            layout_value = self._get_selected_ppt_layout()
            summary_lines.append(f"PPT Layout: {self._get_layout_label(layout_value)}")
            if self.ppt_include_statistics_checkbox.isChecked():
                summary_lines.append("PPT: Statistics slides enabled")
            if self.ppt_include_rms_table_checkbox.isChecked():
                summary_lines.append("PPT: RMS summary table enabled")
                if self.ppt_include_3sigma_columns_checkbox.isChecked():
                    summary_lines.append("PPT: 3-sigma columns included")
        summary_lines.append(f"Output Directory: {self.output_dir_edit.text()}")

        # Total operations estimate
        total_ops = num_channels * (1 if self.full_duration_checkbox.isChecked() else max(1, self.events_table.rowCount()))
        summary_lines.append(f"\nTotal PSD calculations: ~{total_ops}")

        summary_text = "\n".join(summary_lines)

        return show_question(
            self,
            "Confirm Batch Processing",
            f"Ready to start batch processing:\n\n{summary_text}\n\nProceed?"
        )


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = BatchProcessorWindow()
    window.show()
    sys.exit(app.exec())
