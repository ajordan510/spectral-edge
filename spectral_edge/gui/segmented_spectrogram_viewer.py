"""
Segmented Spectrogram Viewer

This module provides a GUI for viewing spectrograms of very long-duration, high sample rate recordings.
Instead of creating one massive spectrogram, it splits the recording into manageable segments
and allows users to navigate through them.

Key Features:
- Handles arbitrarily long recordings without memory issues
- On-demand spectrogram generation with LRU caching
- Navigation controls (First/Prev/Next/Last/Slider)
- Keyboard shortcuts for quick navigation
- Adjustable spectrogram parameters
- Export individual or all segments

Author: SpectralEdge Development Team
Date: 2026-02-08
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QGridLayout, QSlider, QProgressDialog,
    QLineEdit, QCheckBox, QAbstractSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QChildEvent
from PyQt6.QtGui import QFont, QKeyEvent
import os
import numpy as np
from scipy import signal
from typing import List, Tuple, Optional
from collections import OrderedDict
import pyqtgraph as pg
import pyqtgraph.exporters
from matplotlib import colormaps

# Import utilities
from spectral_edge.utils.message_box import show_information, show_warning, show_critical
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.utils.signal_conditioning import apply_processing_pipeline, build_processing_note
from spectral_edge.utils.theme import apply_context_menu_style
from spectral_edge.gui.flight_navigator_enhanced import FlightNavigator


class SpectrogramCache:
    """
    LRU cache for spectrograms to minimize memory usage.
    
    Stores recently generated spectrograms and automatically removes
    oldest entries when cache size limit is reached.
    """
    
    def __init__(self, max_size: int = 10):
        """
        Initialize spectrogram cache.
        
        Parameters
        ----------
        max_size : int, default=10
            Maximum number of spectrograms to cache
        """
        self.cache = OrderedDict()  # Maintains insertion order
        self.max_size = max_size
    
    def get(self, segment_idx: int) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """
        Get spectrogram from cache.
        
        Parameters
        ----------
        segment_idx : int
            Segment index
        
        Returns
        -------
        tuple of (f, t, Sxx) or None
            Spectrogram data if cached, None otherwise
        """
        if segment_idx in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(segment_idx)
            return self.cache[segment_idx]
        return None
    
    def put(self, segment_idx: int, spectrogram: Tuple[np.ndarray, np.ndarray, np.ndarray]):
        """
        Add spectrogram to cache.
        
        Parameters
        ----------
        segment_idx : int
            Segment index
        spectrogram : tuple of (f, t, Sxx)
            Spectrogram data (frequency, time, power)
        """
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)  # Remove oldest (first) item
        
        # Add new spectrogram
        self.cache[segment_idx] = spectrogram
    
    def clear(self):
        """Clear all cached spectrograms."""
        self.cache.clear()


class SpectrogramGenerator(QThread):
    """
    Background thread for generating spectrograms.
    
    Generates spectrograms in background to keep GUI responsive.
    """
    
    generation_complete = pyqtSignal(int, object)  # (segment_idx, (f, t, Sxx))
    generation_error = pyqtSignal(str)
    
    def __init__(self, signal_data: np.ndarray, sample_rate: float,
                 nperseg: int, noverlap: int, window: str):
        """
        Initialize spectrogram generator.
        
        Parameters
        ----------
        signal_data : ndarray
            Signal data for this segment
        sample_rate : float
            Sample rate in Hz
        nperseg : int
            Segment length for each FFT
        noverlap : int
            Overlapping samples between segments
        window : str
            Window function name
        """
        super().__init__()
        self.signal_data = signal_data
        self.sample_rate = sample_rate
        self.nperseg = nperseg
        self.noverlap = noverlap
        self.window = window
        self.segment_idx = 0
    
    def run(self):
        """Generate spectrogram in background thread."""
        try:
            if len(self.signal_data) < 2:
                raise ValueError("Segment is too short to compute a spectrogram")

            nperseg = min(max(2, self.nperseg), len(self.signal_data))
            noverlap = min(max(0, self.noverlap), nperseg - 1)
            
            f, t, Sxx = signal.spectrogram(
                self.signal_data,
                fs=self.sample_rate,
                window=self.window,
                nperseg=nperseg,
                noverlap=noverlap,
                scaling='density'
            )
            
            self.generation_complete.emit(self.segment_idx, (f, t, Sxx))
        
        except Exception as e:
            self.generation_error.emit(str(e))


class SegmentedSpectrogramDisplayWindow(QMainWindow):
    """
    Dedicated popup display window for segmented spectrogram plots.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Segmented Spectrogram Display")
        self.setMinimumSize(1400, 900)
        self.colorbar_item = None
        self._create_ui()
        self._apply_styling()

    def _create_ui(self):
        """Create display UI with plot and navigation controls below it."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        self.segment_info_label = QLabel("No segments generated")
        self.segment_info_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        self.segment_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.segment_info_label)

        self.conditioning_info_label = QLabel("Signal Conditioning: Filter: off | Running Mean Not Removed")
        self.conditioning_info_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        self.conditioning_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.conditioning_info_label.setWordWrap(True)
        main_layout.addWidget(self.conditioning_info_label)

        self.spectrogram_plot = pg.PlotWidget()
        self.spectrogram_plot.setMinimumHeight(700)
        self.spectrogram_plot.setLabel('left', 'Frequency', units='Hz', color='#e0e0e0', size='11pt')
        self.spectrogram_plot.setLabel('bottom', 'Time', units='s', color='#e0e0e0', size='11pt')
        self.spectrogram_plot.setBackground('#1a1f2e')
        self.spectrogram_plot.showGrid(x=True, y=True, alpha=0.25)
        apply_context_menu_style(self.spectrogram_plot)
        main_layout.addWidget(self.spectrogram_plot, stretch=1)

        self.nav_container = QWidget()
        nav_layout = QHBoxLayout(self.nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)

        self.first_button = QPushButton("<< First")
        self.first_button.setEnabled(False)
        nav_layout.addWidget(self.first_button)

        self.prev_button = QPushButton("< Prev")
        self.prev_button.setEnabled(False)
        nav_layout.addWidget(self.prev_button)

        self.segment_slider = QSlider(Qt.Orientation.Horizontal)
        self.segment_slider.setMinimum(0)
        self.segment_slider.setMaximum(0)
        self.segment_slider.setValue(0)
        self.segment_slider.setEnabled(False)
        nav_layout.addWidget(self.segment_slider, stretch=1)

        self.next_button = QPushButton("Next >")
        self.next_button.setEnabled(False)
        nav_layout.addWidget(self.next_button)

        self.last_button = QPushButton("Last >>")
        self.last_button.setEnabled(False)
        nav_layout.addWidget(self.last_button)

        main_layout.addWidget(self.nav_container)

    def _apply_styling(self):
        """Apply dark theme styling for popup."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1f2e;
            }
            QWidget {
                background-color: #1a1f2e;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #4a5568;
                color: #9ca3af;
            }
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 8px;
                background: #2d3748;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: 1px solid #2563eb;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #60a5fa;
            }
        """)

    def set_navigation_enabled(self, enabled: bool):
        """Enable/disable all navigation controls."""
        self.segment_slider.setEnabled(enabled)
        self.first_button.setEnabled(enabled)
        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.last_button.setEnabled(enabled)


class SegmentedSpectrogramViewer(QMainWindow):
    """
    Main window for Segmented Spectrogram Viewer.
    
    Allows users to view spectrograms of very long recordings by splitting
    them into navigable segments.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Segmented Spectrogram Viewer")
        self.setMinimumSize(920, 820)
        
        # State variables
        self.hdf5_loader = None
        self.signal_data = None
        self.sample_rate = None
        self.channel_name = None
        self.flight_key = None
        self.channel_units = ""
        
        self.segments = []  # List of (start_idx, end_idx) tuples
        self.current_segment_idx = 0
        self.spectrogram_cache = SpectrogramCache(max_size=10)
        self.generator_thread = None
        self.display_window = None
        self.mean_window_seconds = 1.0
        self._efficient_fft_base_label = "Use efficient FFT size"
        
        # Create UI
        self._create_ui()
        
        # Apply styling
        self._apply_styling()
        self._enforce_spinbox_button_style()
    
    def _create_ui(self):
        """Create the user interface."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(14, 14, 14, 14)
        
        # Title
        title_label = QLabel("Segmented Spectrogram Viewer")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # File selection
        file_group = self._create_file_selection()
        main_layout.addWidget(file_group)
        
        # Segmentation settings
        seg_group = self._create_segmentation_settings_group()
        main_layout.addWidget(seg_group)

        spec_params_group = self._create_spectrogram_parameters_group()
        main_layout.addWidget(spec_params_group)

        conditioning_group = self._create_signal_conditioning_group()
        main_layout.addWidget(conditioning_group)

        display_params_group = self._create_display_parameters_group()
        main_layout.addWidget(display_params_group)

        self._connect_parameter_signals()

        self.display_hint_label = QLabel(
            "Spectrogram display opens in a dedicated popup window after generation."
        )
        self.display_hint_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        main_layout.addWidget(self.display_hint_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.generate_button = QPushButton("Generate Spectrograms")
        self.generate_button.setMinimumWidth(160)
        self.generate_button.setMinimumHeight(35)
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self._on_generate_clicked)
        button_layout.addWidget(self.generate_button)
        
        self.export_current_button = QPushButton("Export Current")
        self.export_current_button.setMinimumWidth(130)
        self.export_current_button.setMinimumHeight(35)
        self.export_current_button.clicked.connect(self._on_export_current_clicked)
        self.export_current_button.setEnabled(False)
        button_layout.addWidget(self.export_current_button)
        
        self.export_all_button = QPushButton("Export All")
        self.export_all_button.setMinimumWidth(130)
        self.export_all_button.setMinimumHeight(35)
        self.export_all_button.clicked.connect(self._on_export_all_clicked)
        self.export_all_button.setEnabled(False)
        button_layout.addWidget(self.export_all_button)
        
        close_button = QPushButton("Close")
        close_button.setMinimumWidth(130)
        close_button.setMinimumHeight(35)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def _create_file_selection(self) -> QGroupBox:
        """Create file selection group."""
        group = QGroupBox("Input File")
        layout = QGridLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        
        # File path selection
        layout.addWidget(
            QLabel("File:"),
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select HDF5 file...")
        self.file_path_edit.setReadOnly(True)
        layout.addWidget(self.file_path_edit, 0, 1)
        
        browse_button = QPushButton("Browse")
        browse_button.setMinimumWidth(100)
        browse_button.clicked.connect(self._on_browse_file_clicked)
        layout.addWidget(browse_button, 0, 2)
        
        # File info
        self.file_info_label = QLabel("No file selected")
        self.file_info_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        layout.addWidget(self.file_info_label, 1, 0, 1, 3)

        layout.addWidget(
            QLabel("Selected Flight:"),
            2,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.selected_flight_value = QLabel("None selected")
        self.selected_flight_value.setStyleSheet("color: #9ca3af;")
        layout.addWidget(self.selected_flight_value, 2, 1, 1, 2)

        layout.addWidget(
            QLabel("Selected Channel:"),
            3,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.selected_channel_value = QLabel("None selected")
        self.selected_channel_value.setStyleSheet("color: #9ca3af;")
        layout.addWidget(self.selected_channel_value, 3, 1, 1, 2)

        layout.addWidget(
            QLabel("Sample Rate:"),
            4,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.selected_sr_value = QLabel("N/A")
        self.selected_sr_value.setStyleSheet("color: #9ca3af;")
        layout.addWidget(self.selected_sr_value, 4, 1, 1, 2)
        
        layout.setColumnStretch(1, 1)
        group.setLayout(layout)
        return group
    
    def _create_segmentation_settings_group(self) -> QGroupBox:
        """Create segmentation settings group."""
        group = QGroupBox("Segmentation Settings")
        layout = QGridLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        
        # Segment duration
        layout.addWidget(
            QLabel("Segment Duration:"),
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.segment_duration_spin = QDoubleSpinBox()
        self.segment_duration_spin.setMinimum(1.0)
        self.segment_duration_spin.setMaximum(3600.0)
        self.segment_duration_spin.setValue(60.0)
        self.segment_duration_spin.setSuffix(" s")
        self.segment_duration_spin.setMaximumWidth(170)
        self.segment_duration_spin.setEnabled(False)
        layout.addWidget(self.segment_duration_spin, 0, 1)
        
        # Overlap
        layout.addWidget(
            QLabel("Segment Overlap:"),
            0,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.segment_overlap_spin = QSpinBox()
        self.segment_overlap_spin.setMinimum(0)
        self.segment_overlap_spin.setMaximum(90)
        self.segment_overlap_spin.setValue(0)
        self.segment_overlap_spin.setSuffix(" %")
        self.segment_overlap_spin.setEnabled(False)
        self.segment_overlap_spin.setMaximumWidth(170)
        layout.addWidget(self.segment_overlap_spin, 0, 3)
        
        # Total segments display
        self.total_segments_label = QLabel("Total Segments: 0")
        self.total_segments_label.setStyleSheet("color: #60a5fa; font-weight: bold;")
        layout.addWidget(self.total_segments_label, 1, 0, 1, 4)
        
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        group.setLayout(layout)
        return group

    def _create_spectrogram_parameters_group(self) -> QGroupBox:
        """Create spectrogram-parameter controls group."""
        group = QGroupBox("Spectrogram Parameters")
        layout = QGridLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)

        row = 0
        layout.addWidget(
            QLabel("Window:"),
            row,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.window_combo = QComboBox()
        self.window_combo.addItems(['hann', 'hamming', 'blackman', 'bartlett'])
        self.window_combo.setMaximumWidth(170)
        layout.addWidget(self.window_combo, row, 1)
        layout.addWidget(
            QLabel("Spectrogram Overlap (%):"),
            row,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.spec_overlap_spin = QSpinBox()
        self.spec_overlap_spin.setRange(0, 95)
        self.spec_overlap_spin.setValue(75)
        self.spec_overlap_spin.setSuffix(" %")
        self.spec_overlap_spin.setMaximumWidth(170)
        layout.addWidget(self.spec_overlap_spin, row, 3)
        row += 1

        layout.addWidget(
            QLabel("df (Hz):"),
            row,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.df_spin = QDoubleSpinBox()
        self.df_spin.setRange(0.01, 1000.0)
        self.df_spin.setDecimals(2)
        self.df_spin.setSingleStep(0.1)
        self.df_spin.setValue(1.0)
        self.df_spin.setMaximumWidth(170)
        layout.addWidget(self.df_spin, row, 1)

        self.efficient_fft_checkbox = QCheckBox("Use efficient FFT size")
        self.efficient_fft_checkbox.setChecked(True)
        self.efficient_fft_checkbox.setToolTip("Round segment length to nearest power of two for faster FFT computation")
        layout.addWidget(
            QLabel("Efficient FFT Size:"),
            row,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(
            self.efficient_fft_checkbox,
            row,
            3,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        row += 1

        layout.addWidget(
            QLabel("Freq Min (Hz):"),
            row,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0, 1000000)
        self.freq_min_spin.setValue(0.0)
        self.freq_min_spin.setMaximumWidth(170)
        layout.addWidget(self.freq_min_spin, row, 1)

        layout.addWidget(
            QLabel("Freq Max (Hz):"),
            row,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(0, 1000000)
        self.freq_max_spin.setValue(25000.0)
        self.freq_max_spin.setMaximumWidth(170)
        layout.addWidget(self.freq_max_spin, row, 3)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        group.setLayout(layout)
        return group

    def _create_signal_conditioning_group(self) -> QGroupBox:
        """Create signal-conditioning controls group."""
        group = QGroupBox("Signal Conditioning")
        layout = QGridLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)

        row = 0
        layout.addWidget(
            QLabel("Enable Filter:"),
            row,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.conditioning_filter_checkbox = QCheckBox("Enable")
        layout.addWidget(
            self.conditioning_filter_checkbox,
            row,
            1,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        layout.addWidget(
            QLabel("Filter Type:"),
            row,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.conditioning_filter_type_combo = QComboBox()
        self.conditioning_filter_type_combo.addItems(["lowpass", "highpass", "bandpass"])
        self.conditioning_filter_type_combo.setCurrentText("bandpass")
        self.conditioning_filter_type_combo.setMaximumWidth(170)
        self.conditioning_filter_type_combo.setEnabled(False)
        layout.addWidget(self.conditioning_filter_type_combo, row, 3)
        row += 1

        self.conditioning_low_cutoff_label = QLabel("Low Cutoff (Hz):")
        layout.addWidget(
            self.conditioning_low_cutoff_label,
            row,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.conditioning_low_cutoff_spin = QDoubleSpinBox()
        self.conditioning_low_cutoff_spin.setRange(0.1, 1000000.0)
        self.conditioning_low_cutoff_spin.setDecimals(2)
        self.conditioning_low_cutoff_spin.setSingleStep(1.0)
        self.conditioning_low_cutoff_spin.setValue(100.0)
        self.conditioning_low_cutoff_spin.setMaximumWidth(170)
        self.conditioning_low_cutoff_spin.setEnabled(False)
        layout.addWidget(self.conditioning_low_cutoff_spin, row, 1)

        self.conditioning_high_cutoff_label = QLabel("High Cutoff (Hz):")
        layout.addWidget(
            self.conditioning_high_cutoff_label,
            row,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.conditioning_high_cutoff_spin = QDoubleSpinBox()
        self.conditioning_high_cutoff_spin.setRange(0.1, 1000000.0)
        self.conditioning_high_cutoff_spin.setDecimals(2)
        self.conditioning_high_cutoff_spin.setSingleStep(1.0)
        self.conditioning_high_cutoff_spin.setValue(2000.0)
        self.conditioning_high_cutoff_spin.setMaximumWidth(170)
        self.conditioning_high_cutoff_spin.setEnabled(False)
        layout.addWidget(self.conditioning_high_cutoff_spin, row, 3)
        row += 1

        layout.addWidget(
            QLabel("Remove Running Mean:"),
            row,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.conditioning_remove_mean_checkbox = QCheckBox("Remove")
        layout.addWidget(
            self.conditioning_remove_mean_checkbox,
            row,
            1,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        row += 1

        self.conditioning_design_label = QLabel("Filter Design: 6th-order Butterworth")
        self.conditioning_design_label.setStyleSheet("color: #9ca3af;")
        self.conditioning_design_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.conditioning_design_label, row, 2, 1, 2)
        row += 1

        self.conditioning_note_label = QLabel("Signal Conditioning: Filter: off | Running Mean Not Removed")
        self.conditioning_note_label.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        self.conditioning_note_label.setWordWrap(True)
        self.conditioning_note_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.conditioning_note_label, row, 0, 1, 4)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        group.setLayout(layout)
        return group

    def _create_display_parameters_group(self) -> QGroupBox:
        """Create display controls group."""
        group = QGroupBox("Display Parameters")
        layout = QGridLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)

        row = 0
        layout.addWidget(
            QLabel("Show Colorbar:"),
            row,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.show_colorbar_checkbox = QCheckBox("Show")
        self.show_colorbar_checkbox.setChecked(True)
        layout.addWidget(
            self.show_colorbar_checkbox,
            row,
            1,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )

        layout.addWidget(
            QLabel("Colormap:"),
            row,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(['viridis', 'plasma', 'inferno', 'magma', 'jet', 'hot', 'cool'])
        self.colormap_combo.setCurrentText('viridis')
        self.colormap_combo.setMaximumWidth(170)
        layout.addWidget(self.colormap_combo, row, 3)
        row += 1

        layout.addWidget(
            QLabel("SNR (dB):"),
            row,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.snr_spin = QSpinBox()
        self.snr_spin.setRange(10, 100)
        self.snr_spin.setSingleStep(5)
        self.snr_spin.setValue(60)
        self.snr_spin.setMaximumWidth(170)
        layout.addWidget(self.snr_spin, row, 3)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        group.setLayout(layout)
        return group

    def _connect_parameter_signals(self):
        """Wire UI control changes to refresh/replot behavior."""
        self.segment_duration_spin.valueChanged.connect(self._update_total_segments_preview)
        self.segment_overlap_spin.valueChanged.connect(self._update_total_segments_preview)

        self.df_spin.valueChanged.connect(self._refresh_actual_df_preview)
        self.efficient_fft_checkbox.toggled.connect(self._refresh_actual_df_preview)
        self.spec_overlap_spin.valueChanged.connect(self._refresh_actual_df_preview)

        self.conditioning_filter_checkbox.toggled.connect(self._on_conditioning_filter_enabled_changed)
        self.conditioning_filter_checkbox.toggled.connect(self._on_conditioning_controls_changed)
        self.conditioning_filter_type_combo.currentTextChanged.connect(self._on_conditioning_filter_type_changed)
        self.conditioning_filter_type_combo.currentTextChanged.connect(self._on_conditioning_controls_changed)
        self.conditioning_low_cutoff_spin.valueChanged.connect(self._on_conditioning_controls_changed)
        self.conditioning_high_cutoff_spin.valueChanged.connect(self._on_conditioning_controls_changed)
        self.conditioning_remove_mean_checkbox.toggled.connect(self._on_conditioning_controls_changed)

        self.colormap_combo.currentTextChanged.connect(self._replot_current_from_cache)
        self.snr_spin.valueChanged.connect(self._replot_current_from_cache)
        self.show_colorbar_checkbox.toggled.connect(self._replot_current_from_cache)
        self.freq_min_spin.valueChanged.connect(self._replot_current_from_cache)
        self.freq_max_spin.valueChanged.connect(self._replot_current_from_cache)

        self._refresh_actual_df_preview()
        self._on_conditioning_filter_type_changed()
        self._update_conditioning_note_labels()

    def _apply_styling(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1f2e;
            }
            QWidget {
                background-color: #1a1f2e;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 1px solid #4a5568;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #4a5568;
                color: #9ca3af;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 4px;
                padding: 4px;
                color: #e0e0e0;
            }
            QSpinBox, QDoubleSpinBox {
                padding-right: 24px;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #4a5568;
                border-bottom: 1px solid #4a5568;
                background-color: #3d4758;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 18px;
                border-left: 1px solid #4a5568;
                background-color: #3d4758;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #4d5768;
            }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 7px solid #e0e0e0;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid #e0e0e0;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border: 1px solid #60a5fa;
            }
            QSlider::groove:horizontal {
                border: 1px solid #4a5568;
                height: 8px;
                background: #2d3748;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: 1px solid #2563eb;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #60a5fa;
            }
        """)

    def _enforce_spinbox_button_style(self):
        """Force robust up/down arrow behavior for all spinboxes."""
        for spin in self.findChildren(QAbstractSpinBox):
            self._configure_spinbox(spin)

    def _configure_spinbox(self, spin: QAbstractSpinBox):
        """Apply explicit up/down controls to a spinbox."""
        if spin is None:
            return
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        spin.setAccelerated(True)

    def childEvent(self, event: QChildEvent):
        """Ensure dynamically created spinboxes use up/down arrows."""
        super().childEvent(event)
        child = event.child()
        if isinstance(child, QAbstractSpinBox):
            self._configure_spinbox(child)

    def showEvent(self, event):
        """Re-apply spinbox style after Qt style/polish passes."""
        self._enforce_spinbox_button_style()
        super().showEvent(event)

    def _ensure_display_window(self):
        """Create popup display window and connect navigation if needed."""
        if self.display_window is None:
            self.display_window = SegmentedSpectrogramDisplayWindow()
            self.display_window.first_button.clicked.connect(self._on_first_clicked)
            self.display_window.prev_button.clicked.connect(self._on_prev_clicked)
            self.display_window.next_button.clicked.connect(self._on_next_clicked)
            self.display_window.last_button.clicked.connect(self._on_last_clicked)
            self.display_window.segment_slider.valueChanged.connect(self._on_slider_changed)

        self._update_conditioning_note_labels()
        self.display_window.show()
        self.display_window.raise_()

    def _set_navigation_enabled(self, enabled: bool):
        """Enable or disable navigation controls on popup window."""
        if self.display_window is not None:
            self.display_window.set_navigation_enabled(enabled)

    def _refresh_actual_df_preview(self):
        """Update the actual df preview based on sample rate and FFT settings."""
        if self.sample_rate and self.sample_rate > 0:
            _, _, actual_df = self._calculate_fft_parameters()
            self.efficient_fft_checkbox.setText(
                f"{self._efficient_fft_base_label} (actual df = {actual_df:.3f} Hz)"
            )
        else:
            self.efficient_fft_checkbox.setText(
                f"{self._efficient_fft_base_label} (actual df = --)"
            )

    def _update_total_segments_preview(self, *_args):
        """Update total-segment count immediately when segment controls change."""
        if self.signal_data is None or self.sample_rate is None or self.sample_rate <= 0:
            self.total_segments_label.setText("Total Segments: 0")
            return

        segment_samples = int(self.segment_duration_spin.value() * self.sample_rate)
        if segment_samples <= 0:
            self.total_segments_label.setText("Total Segments: 0")
            return

        overlap_samples = int(segment_samples * self.segment_overlap_spin.value() / 100.0)
        step_samples = max(1, segment_samples - overlap_samples)
        total_samples = len(self.signal_data)
        if total_samples <= 0:
            self.total_segments_label.setText("Total Segments: 0")
            return

        segments_count = 0
        start_idx = 0
        while start_idx < total_samples:
            end_idx = min(start_idx + segment_samples, total_samples)
            segments_count += 1
            if end_idx >= total_samples:
                break
            start_idx += step_samples

        self.total_segments_label.setText(f"Total Segments: {segments_count}")

    def _build_conditioning_filter_settings(self) -> dict:
        """Build shared filter-settings payload from segmented-viewer controls."""
        enabled = self.conditioning_filter_checkbox.isChecked()
        filter_type = self.conditioning_filter_type_combo.currentText().strip().lower()
        user_highpass = None
        user_lowpass = None
        if enabled:
            if filter_type in {"highpass", "bandpass"}:
                user_highpass = self.conditioning_low_cutoff_spin.value()
            if filter_type in {"lowpass", "bandpass"}:
                user_lowpass = self.conditioning_high_cutoff_spin.value()
        return {
            "enabled": enabled,
            "filter_type": filter_type,
            "filter_design": "butterworth",
            "filter_order": 6,
            "user_highpass_hz": user_highpass,
            "user_lowpass_hz": user_lowpass,
            "cutoff_low": self.conditioning_low_cutoff_spin.value(),
            "cutoff_high": self.conditioning_high_cutoff_spin.value(),
        }

    def _on_conditioning_filter_enabled_changed(self, enabled: bool):
        """Enable/disable filter controls."""
        self.conditioning_filter_type_combo.setEnabled(enabled)
        self._on_conditioning_filter_type_changed()

    def _on_conditioning_filter_type_changed(self, *_args):
        """Show/hide cutoff controls based on selected filter type."""
        filter_type = self.conditioning_filter_type_combo.currentText().strip().lower()
        enabled = self.conditioning_filter_checkbox.isChecked()
        show_low = filter_type in {"highpass", "bandpass"}
        show_high = filter_type in {"lowpass", "bandpass"}

        self.conditioning_low_cutoff_label.setVisible(show_low)
        self.conditioning_low_cutoff_spin.setVisible(show_low)
        self.conditioning_high_cutoff_label.setVisible(show_high)
        self.conditioning_high_cutoff_spin.setVisible(show_high)

        self.conditioning_low_cutoff_spin.setEnabled(enabled and show_low)
        self.conditioning_high_cutoff_spin.setEnabled(enabled and show_high)

    def _on_conditioning_controls_changed(self, *_args):
        """Refresh conditioning labels when any conditioning control changes."""
        self._update_conditioning_note_labels()

    def _update_conditioning_note_labels(self):
        """Update conditioning summary text in parameter and display windows."""
        note = build_processing_note(
            filter_settings=self._build_conditioning_filter_settings(),
            remove_mean=self.conditioning_remove_mean_checkbox.isChecked(),
            mean_window_seconds=self.mean_window_seconds,
        )
        if hasattr(self, "conditioning_note_label"):
            self.conditioning_note_label.setText(f"Signal Conditioning: {note}")
        if self.display_window is not None and hasattr(self.display_window, "conditioning_info_label"):
            self.display_window.conditioning_info_label.setText(f"Signal Conditioning: {note}")

    def _calculate_fft_parameters(self, sample_count: Optional[int] = None) -> Tuple[int, int, float]:
        """Compute nperseg/noverlap from df and overlap controls."""
        if not self.sample_rate or self.sample_rate <= 0:
            return 256, 128, 0.0

        requested_df = max(self.df_spin.value(), 1e-6)
        nperseg = max(2, int(round(self.sample_rate / requested_df)))

        if self.efficient_fft_checkbox.isChecked() and nperseg > 1:
            nperseg = 2 ** int(np.ceil(np.log2(nperseg)))

        if sample_count is not None:
            nperseg = min(nperseg, max(2, sample_count))

        noverlap = int(round(nperseg * self.spec_overlap_spin.value() / 100.0))
        noverlap = min(max(0, noverlap), nperseg - 1)
        actual_df = self.sample_rate / float(nperseg)
        return nperseg, noverlap, actual_df

    def _remove_colorbar(self):
        """Remove existing colorbar from popup display."""
        if self.display_window is None or self.display_window.colorbar_item is None:
            return
        try:
            self.display_window.spectrogram_plot.plotItem.layout.removeItem(self.display_window.colorbar_item)
        except Exception:
            pass
        self.display_window.colorbar_item = None

    def _replot_current_from_cache(self):
        """Re-render current segment using cached data and display settings."""
        if not self.segments or self.sample_rate is None:
            return

        cached_spec = self.spectrogram_cache.get(self.current_segment_idx)
        if cached_spec is None:
            return

        start_idx, _ = self.segments[self.current_segment_idx]
        start_time = start_idx / self.sample_rate
        f, t, Sxx = cached_spec
        self._plot_spectrogram(f, t, Sxx, start_time)
    
    # Event handlers
    
    def _on_browse_file_clicked(self):
        """Handle browse file button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select HDF5 File", "", "HDF5 Files (*.h5 *.hdf5);;All Files (*)"
        )
        
        if file_path:
            self._load_hdf5_file(file_path)
    
    def _load_hdf5_file(self, file_path: str):
        """Load HDF5 file and launch enhanced navigator for channel selection."""
        try:
            if self.hdf5_loader is not None:
                self.hdf5_loader.close()

            self.hdf5_loader = HDF5FlightDataLoader(file_path)
            
            # Update file path display
            self.file_path_edit.setText(file_path)
            
            # Get file info
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            self.file_info_label.setText(f"Size: {file_size_mb:.1f} MB")
            self.file_info_label.setStyleSheet("color: #60a5fa;")

            selected_item = self._launch_channel_navigator()
            if selected_item is None:
                self._clear_selected_channel()
                return

            self._apply_selected_channel(*selected_item)

        except Exception as e:
            show_critical(self, "Error Loading File", f"Failed to load HDF5 file:\n\n{str(e)}")
            self.file_info_label.setText("Error loading file")
            self.file_info_label.setStyleSheet("color: #ef4444;")
            self._clear_selected_channel()

    def _launch_channel_navigator(self) -> Optional[Tuple[str, str, object]]:
        """Launch enhanced flight navigator and return one selected item."""
        if self.hdf5_loader is None:
            return None

        navigator = FlightNavigator(
            self.hdf5_loader,
            self,
            max_selected_channels=1,
            selection_limit_message=(
                "Segmented Spectrogram Viewer supports one channel at a time. "
                "Select one channel or cancel."
            ),
        )
        navigator.setModal(True)

        if navigator.exec() != navigator.DialogCode.Accepted:
            return None

        if len(navigator.selected_items) != 1:
            show_warning(
                self,
                "Selection Required",
                "Please select exactly one channel to continue.",
            )
            return None

        return navigator.selected_items[0]

    def _clear_selected_channel(self):
        """Clear currently selected channel state and disable generation."""
        self.signal_data = None
        self.sample_rate = None
        self.channel_name = None
        self.flight_key = None
        self.channel_units = ""
        self.segments = []
        self.current_segment_idx = 0
        self.spectrogram_cache.clear()
        self.total_segments_label.setText("Total Segments: 0")
        self.selected_flight_value.setText("None selected")
        self.selected_channel_value.setText("None selected")
        self.selected_sr_value.setText("N/A")
        self.selected_flight_value.setStyleSheet("color: #9ca3af;")
        self.selected_channel_value.setStyleSheet("color: #9ca3af;")
        self.selected_sr_value.setStyleSheet("color: #9ca3af;")
        self.segment_duration_spin.setEnabled(False)
        self.segment_overlap_spin.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.export_current_button.setEnabled(False)
        self.export_all_button.setEnabled(False)
        self._set_navigation_enabled(False)
        self._refresh_actual_df_preview()

    def _apply_selected_channel(self, flight_key: str, channel_name: str, channel_info):
        """Load selected channel data and update UI state."""
        if self.hdf5_loader is None:
            return

        try:
            data_dict = self.hdf5_loader.load_channel_data(
                flight_key,
                channel_name,
                decimate_for_display=False,
            )
        except Exception as e:
            show_critical(self, "Error", f"Failed to load channel data:\n\n{str(e)}")
            self._clear_selected_channel()
            return

        self.signal_data = data_dict['data_full']
        self.sample_rate = float(data_dict['sample_rate'])
        self.channel_name = channel_name
        self.flight_key = flight_key
        self.channel_units = str(getattr(channel_info, "units", "") or "")
        self.segments = []
        self.current_segment_idx = 0
        self.spectrogram_cache.clear()
        self.total_segments_label.setText("Total Segments: 0")

        duration = len(self.signal_data) / self.sample_rate
        self.file_info_label.setText(
            f"Size: {os.path.getsize(self.file_path_edit.text()) / (1024 * 1024):.1f} MB | "
            f"Duration: {duration:.1f}s | "
            f"Sample Rate: {self.sample_rate:.0f} Hz"
        )
        self.file_info_label.setStyleSheet("color: #60a5fa;")

        self.selected_flight_value.setText(str(flight_key))
        self.selected_channel_value.setText(str(channel_name))
        self.selected_sr_value.setText(f"{self.sample_rate:.3f} Hz")
        self.selected_flight_value.setStyleSheet("color: #e0e0e0;")
        self.selected_channel_value.setStyleSheet("color: #e0e0e0;")
        self.selected_sr_value.setStyleSheet("color: #e0e0e0;")

        self.segment_duration_spin.setEnabled(True)
        self.segment_overlap_spin.setEnabled(True)
        self.generate_button.setEnabled(True)
        self.export_current_button.setEnabled(False)
        self.export_all_button.setEnabled(False)

        nyquist = self.sample_rate / 2.0
        self.freq_max_spin.setMaximum(nyquist)
        self.freq_max_spin.setValue(min(nyquist, 25000.0))
        if self.freq_min_spin.value() > self.freq_max_spin.value():
            self.freq_min_spin.setValue(self.freq_max_spin.value())
        self._refresh_actual_df_preview()
        self._update_total_segments_preview()

    def _on_generate_clicked(self):
        """Handle generate spectrograms button click."""
        if self.signal_data is None or self.sample_rate is None:
            return
        self._update_conditioning_note_labels()

        segment_duration = self.segment_duration_spin.value()
        overlap_pct = self.segment_overlap_spin.value()

        segment_samples = int(segment_duration * self.sample_rate)
        overlap_samples = int(segment_samples * overlap_pct / 100.0)
        step_samples = max(1, segment_samples - overlap_samples)

        total_samples = len(self.signal_data)

        self.segments = []
        start_idx = 0
        while start_idx < total_samples:
            end_idx = min(start_idx + segment_samples, total_samples)
            self.segments.append((start_idx, end_idx))
            if end_idx >= total_samples:
                break
            start_idx += step_samples

        self.total_segments_label.setText(f"Total Segments: {len(self.segments)}")
        if not self.segments:
            self._set_navigation_enabled(False)
            self.export_current_button.setEnabled(False)
            self.export_all_button.setEnabled(False)
            return

        self.current_segment_idx = min(self.current_segment_idx, len(self.segments) - 1)

        self._ensure_display_window()
        self.display_window.segment_slider.setMaximum(max(0, len(self.segments) - 1))
        self.display_window.segment_slider.setValue(self.current_segment_idx)
        self._set_navigation_enabled(True)

        self.export_current_button.setEnabled(True)
        self.export_all_button.setEnabled(True)

        self.spectrogram_cache.clear()
        self._display_segment(self.current_segment_idx)

    def _display_segment(self, segment_idx: int):
        """Display spectrogram for the given segment."""
        if segment_idx < 0 or segment_idx >= len(self.segments) or self.sample_rate is None:
            return

        self._ensure_display_window()
        self.current_segment_idx = segment_idx

        start_idx, end_idx = self.segments[segment_idx]
        start_time = start_idx / self.sample_rate
        end_time = end_idx / self.sample_rate
        duration = (end_idx - start_idx) / self.sample_rate

        self.display_window.segment_info_label.setText(
            f"Segment {segment_idx + 1} of {len(self.segments)} | "
            f"Time: {start_time:.2f}s - {end_time:.2f}s ({duration:.2f}s)"
        )
        self.display_window.segment_info_label.setStyleSheet("color: #60a5fa; font-weight: bold;")

        self.display_window.segment_slider.blockSignals(True)
        self.display_window.segment_slider.setValue(segment_idx)
        self.display_window.segment_slider.blockSignals(False)

        cached_spec = self.spectrogram_cache.get(segment_idx)
        if cached_spec is not None:
            f, t, Sxx = cached_spec
            self._plot_spectrogram(f, t, Sxx, start_time)
            return

        segment_data = self.signal_data[start_idx:end_idx]
        conditioned_segment_data = apply_processing_pipeline(
            segment_data,
            self.sample_rate,
            filter_settings=self._build_conditioning_filter_settings(),
            remove_mean=self.conditioning_remove_mean_checkbox.isChecked(),
            mean_window_seconds=self.mean_window_seconds,
        )
        nperseg, noverlap, _ = self._calculate_fft_parameters(sample_count=len(conditioned_segment_data))
        window = self.window_combo.currentText().lower()

        self.generator_thread = SpectrogramGenerator(
            conditioned_segment_data,
            self.sample_rate,
            nperseg,
            noverlap,
            window,
        )
        self.generator_thread.segment_idx = segment_idx
        self.generator_thread.generation_complete.connect(self._on_spectrogram_generated)
        self.generator_thread.generation_error.connect(self._on_generation_error)
        self.generator_thread.start()

        self.display_window.segment_info_label.setText(
            f"Generating spectrogram for segment {segment_idx + 1}..."
        )
        self._update_conditioning_note_labels()

    def _on_spectrogram_generated(self, segment_idx: int, spectrogram_data):
        """Handle spectrogram generation completion."""
        f, t, Sxx = spectrogram_data
        self.spectrogram_cache.put(segment_idx, (f, t, Sxx))

        if segment_idx == self.current_segment_idx and self.sample_rate is not None:
            start_idx, _ = self.segments[segment_idx]
            start_time = start_idx / self.sample_rate
            self._plot_spectrogram(f, t, Sxx, start_time)

    def _on_generation_error(self, error_msg: str):
        """Handle spectrogram generation error."""
        show_critical(self, "Generation Error", f"Failed to generate spectrogram:\n\n{error_msg}")

    def _plot_spectrogram(self, f: np.ndarray, t: np.ndarray, Sxx: np.ndarray, start_time: float):
        """Plot spectrogram on the popup display."""
        if self.display_window is None:
            return

        if len(f) == 0 or len(t) == 0:
            self.display_window.spectrogram_plot.clear()
            return

        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()

        actual_min = max(freq_min, float(f[0]))
        actual_max = min(freq_max, float(f[-1]))
        freq_mask = (f >= actual_min) & (f <= actual_max)

        f_filtered = f[freq_mask]
        Sxx_filtered = Sxx[freq_mask, :]

        if len(f_filtered) == 0:
            self.display_window.spectrogram_plot.clear()
            return

        Sxx_db = 10.0 * np.log10(np.maximum(Sxx_filtered, 1e-20))
        self._render_spectrogram(f_filtered, t, Sxx_db, start_time)

    def _render_spectrogram(self, f_filtered: np.ndarray, t: np.ndarray, Sxx_db: np.ndarray, start_time: float):
        """Render spectrogram with display settings (colormap/SNR/colorbar/limits)."""
        plot = self.display_window.spectrogram_plot
        plot.clear()

        max_power = float(np.nanmax(Sxx_db))
        min_power = max_power - float(self.snr_spin.value())

        img = pg.ImageItem()
        img.setImage(Sxx_db.T, autoLevels=False, levels=(min_power, max_power))

        t_start = start_time + float(t[0])
        t_end = start_time + float(t[-1])
        f_start = float(f_filtered[0])
        f_end = float(f_filtered[-1])

        img.setRect(pg.QtCore.QRectF(
            t_start,
            f_start,
            max(t_end - t_start, 1e-9),
            max(f_end - f_start, 1e-9)
        ))

        cmap_name = self.colormap_combo.currentText()
        mpl_cmap = colormaps.get_cmap(cmap_name)
        lut = (mpl_cmap(np.linspace(0, 1, 256)) * 255).astype(np.ubyte)
        img.setLookupTable(np.ascontiguousarray(lut))
        plot.addItem(img)

        plot.setLabel('left', 'Frequency', units='Hz', color='#e0e0e0', size='11pt')
        plot.setLabel('bottom', 'Time', units='s', color='#e0e0e0', size='11pt')
        plot.setTitle(
            f"{self.channel_name or 'Channel'} | Segment {self.current_segment_idx + 1}/{len(self.segments)} | "
            f"SNR: {self.snr_spin.value()} dB",
            color='#e0e0e0',
            size='12pt'
        )

        self._remove_colorbar()
        if self.show_colorbar_checkbox.isChecked():
            pg_colormap = pg.ColorMap(np.linspace(0, 1, 256), np.ascontiguousarray(lut))
            colorbar = pg.ColorBarItem(
                values=(min_power, max_power),
                colorMap=pg_colormap,
                label='Power (dB)',
                limits=(min_power, max_power),
                interactive=False,
                width=20,
                pen='#e0e0e0',
                hoverPen='#ffffff',
                hoverBrush='#2d3748',
            )
            colorbar.setImageItem(img, insert_in=plot.plotItem)
            colorbar.axis.setPen('#e0e0e0')
            colorbar.axis.setTextPen('#e0e0e0')
            self.display_window.colorbar_item = colorbar

        plot.setXRange(t_start, t_end, padding=0.02)
        plot.setYRange(f_start, f_end, padding=0.02)

    def _on_first_clicked(self):
        """Navigate to first segment."""
        if self.display_window is not None:
            self.display_window.segment_slider.setValue(0)

    def _on_prev_clicked(self):
        """Navigate to previous segment."""
        if self.display_window is not None and self.current_segment_idx > 0:
            self.display_window.segment_slider.setValue(self.current_segment_idx - 1)

    def _on_next_clicked(self):
        """Navigate to next segment."""
        if self.display_window is not None and self.current_segment_idx < len(self.segments) - 1:
            self.display_window.segment_slider.setValue(self.current_segment_idx + 1)

    def _on_last_clicked(self):
        """Navigate to last segment."""
        if self.display_window is not None and len(self.segments) > 0:
            self.display_window.segment_slider.setValue(len(self.segments) - 1)

    def _on_slider_changed(self, value: int):
        """Handle slider value change."""
        self._display_segment(value)

    def _on_export_current_clicked(self):
        """Export current segment spectrogram."""
        if self.current_segment_idx >= len(self.segments):
            return

        self._ensure_display_window()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Spectrogram",
            "",
            "PNG Image (*.png);;All Files (*)"
        )

        if not file_path:
            return

        if not file_path.endswith('.png'):
            file_path += '.png'

        try:
            exporter = pg.exporters.ImageExporter(self.display_window.spectrogram_plot.plotItem)
            exporter.export(file_path)
            show_information(self, "Export Complete", f"Spectrogram saved to:\n{file_path}")

        except Exception as e:
            show_critical(self, "Export Error", f"Failed to export spectrogram:\n\n{str(e)}")

    def _on_export_all_clicked(self):
        """Export all segment spectrograms."""
        if not self.segments:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for All Spectrograms"
        )

        if not output_dir:
            return

        self._ensure_display_window()

        progress = QProgressDialog(
            "Exporting spectrograms...", "Cancel", 0, len(self.segments), self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        try:
            from PyQt6.QtWidgets import QApplication

            for i in range(len(self.segments)):
                if progress.wasCanceled():
                    break

                progress.setValue(i)
                progress.setLabelText(f"Exporting segment {i + 1} of {len(self.segments)}...")

                if self.spectrogram_cache.get(i) is None:
                    start_idx, end_idx = self.segments[i]
                    segment_data = self.signal_data[start_idx:end_idx]
                    conditioned_segment_data = apply_processing_pipeline(
                        segment_data,
                        self.sample_rate,
                        filter_settings=self._build_conditioning_filter_settings(),
                        remove_mean=self.conditioning_remove_mean_checkbox.isChecked(),
                        mean_window_seconds=self.mean_window_seconds,
                    )

                    nperseg, noverlap, _ = self._calculate_fft_parameters(sample_count=len(conditioned_segment_data))
                    window = self.window_combo.currentText().lower()

                    f, t, Sxx = signal.spectrogram(
                        conditioned_segment_data,
                        fs=self.sample_rate,
                        window=window,
                        nperseg=nperseg,
                        noverlap=noverlap,
                        scaling='density'
                    )

                    self.spectrogram_cache.put(i, (f, t, Sxx))

                self.current_segment_idx = i
                self.display_window.segment_slider.blockSignals(True)
                self.display_window.segment_slider.setValue(i)
                self.display_window.segment_slider.blockSignals(False)

                start_idx, _ = self.segments[i]
                start_time = start_idx / self.sample_rate
                f, t, sxx = self.spectrogram_cache.get(i)
                self._plot_spectrogram(f, t, sxx, start_time)

                QApplication.processEvents()

                file_path = os.path.join(output_dir, f"spectrogram_segment_{i+1:03d}.png")
                exporter = pg.exporters.ImageExporter(self.display_window.spectrogram_plot.plotItem)
                exporter.export(file_path)

            progress.setValue(len(self.segments))

            show_information(
                self,
                "Export Complete",
                f"Exported {len(self.segments)} spectrograms to:\n{output_dir}"
            )

        except Exception as e:
            show_critical(self, "Export Error", f"Failed to export spectrograms:\n\n{str(e)}")

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Left:
            self._on_prev_clicked()
        elif event.key() == Qt.Key.Key_Right:
            self._on_next_clicked()
        elif event.key() == Qt.Key.Key_Home:
            self._on_first_clicked()
        elif event.key() == Qt.Key.Key_End:
            self._on_last_clicked()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Close popup display window when controller closes."""
        if self.display_window is not None:
            self.display_window.close()
        super().closeEvent(event)
