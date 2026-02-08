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
    QGroupBox, QGridLayout, QMessageBox, QSlider, QProgressDialog,
    QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent
import os
import sys
import numpy as np
import h5py
from scipy import signal
from typing import List, Tuple, Optional, Dict
from collections import OrderedDict
import pyqtgraph as pg

# Import utilities
from spectral_edge.utils.message_box import show_information, show_warning, show_critical
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader


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
                 nfft: int, overlap_pct: int, window: str):
        """
        Initialize spectrogram generator.
        
        Parameters
        ----------
        signal_data : ndarray
            Signal data for this segment
        sample_rate : float
            Sample rate in Hz
        nfft : int
            FFT size
        overlap_pct : int
            Overlap percentage (0-99)
        window : str
            Window function name
        """
        super().__init__()
        self.signal_data = signal_data
        self.sample_rate = sample_rate
        self.nfft = nfft
        self.overlap_pct = overlap_pct
        self.window = window
        self.segment_idx = 0
    
    def run(self):
        """Generate spectrogram in background thread."""
        try:
            noverlap = int(self.nfft * self.overlap_pct / 100)
            
            f, t, Sxx = signal.spectrogram(
                self.signal_data,
                fs=self.sample_rate,
                window=self.window,
                nperseg=self.nfft,
                noverlap=noverlap,
                scaling='density'
            )
            
            self.generation_complete.emit(self.segment_idx, (f, t, Sxx))
        
        except Exception as e:
            self.generation_error.emit(str(e))


class SegmentedSpectrogramViewer(QMainWindow):
    """
    Main window for Segmented Spectrogram Viewer.
    
    Allows users to view spectrograms of very long recordings by splitting
    them into navigable segments.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Segmented Spectrogram Viewer")
        self.setMinimumSize(1000, 800)
        
        # State variables
        self.hdf5_loader = None
        self.signal_data = None
        self.sample_rate = None
        self.channel_name = None
        self.flight_key = None
        
        self.segments = []  # List of (start_idx, end_idx) tuples
        self.current_segment_idx = 0
        self.spectrogram_cache = SpectrogramCache(max_size=10)
        self.generator_thread = None
        
        # Create UI
        self._create_ui()
        
        # Apply styling
        self._apply_styling()
    
    def _create_ui(self):
        """Create the user interface."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
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
        seg_group = self._create_segmentation_settings()
        main_layout.addWidget(seg_group)
        
        # Spectrogram display
        display_group = self._create_spectrogram_display()
        main_layout.addWidget(display_group)
        
        # Spectrogram parameters
        params_group = self._create_spectrogram_parameters()
        main_layout.addWidget(params_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.export_current_button = QPushButton("Export Current")
        self.export_current_button.setMinimumWidth(120)
        self.export_current_button.setMinimumHeight(35)
        self.export_current_button.clicked.connect(self._on_export_current_clicked)
        self.export_current_button.setEnabled(False)
        button_layout.addWidget(self.export_current_button)
        
        self.export_all_button = QPushButton("Export All")
        self.export_all_button.setMinimumWidth(120)
        self.export_all_button.setMinimumHeight(35)
        self.export_all_button.clicked.connect(self._on_export_all_clicked)
        self.export_all_button.setEnabled(False)
        button_layout.addWidget(self.export_all_button)
        
        close_button = QPushButton("Close")
        close_button.setMinimumWidth(120)
        close_button.setMinimumHeight(35)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def _create_file_selection(self) -> QGroupBox:
        """Create file selection group."""
        group = QGroupBox("Input File")
        layout = QGridLayout()
        
        # File path selection
        layout.addWidget(QLabel("File:"), 0, 0)
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
        
        # Flight selection
        layout.addWidget(QLabel("Flight:"), 2, 0)
        self.flight_combo = QComboBox()
        self.flight_combo.setEnabled(False)
        self.flight_combo.currentTextChanged.connect(self._on_flight_changed)
        layout.addWidget(self.flight_combo, 2, 1, 1, 2)
        
        # Channel selection
        layout.addWidget(QLabel("Channel:"), 3, 0)
        self.channel_combo = QComboBox()
        self.channel_combo.setEnabled(False)
        self.channel_combo.currentTextChanged.connect(self._on_channel_changed)
        layout.addWidget(self.channel_combo, 3, 1, 1, 2)
        
        group.setLayout(layout)
        return group
    
    def _create_segmentation_settings(self) -> QGroupBox:
        """Create segmentation settings group."""
        group = QGroupBox("Segmentation Settings")
        layout = QGridLayout()
        
        # Segment duration
        layout.addWidget(QLabel("Segment Duration:"), 0, 0)
        self.segment_duration_spin = QDoubleSpinBox()
        self.segment_duration_spin.setMinimum(1.0)
        self.segment_duration_spin.setMaximum(3600.0)
        self.segment_duration_spin.setValue(60.0)
        self.segment_duration_spin.setSuffix(" seconds")
        self.segment_duration_spin.setEnabled(False)
        layout.addWidget(self.segment_duration_spin, 0, 1)
        
        # Overlap
        layout.addWidget(QLabel("Overlap:"), 1, 0)
        self.segment_overlap_spin = QSpinBox()
        self.segment_overlap_spin.setMinimum(0)
        self.segment_overlap_spin.setMaximum(90)
        self.segment_overlap_spin.setValue(50)
        self.segment_overlap_spin.setSuffix(" %")
        self.segment_overlap_spin.setEnabled(False)
        layout.addWidget(self.segment_overlap_spin, 1, 1)
        
        # Total segments display
        self.total_segments_label = QLabel("Total Segments: 0")
        self.total_segments_label.setStyleSheet("color: #60a5fa; font-weight: bold;")
        layout.addWidget(self.total_segments_label, 2, 0, 1, 2)
        
        # Generate button
        self.generate_button = QPushButton("Generate Spectrograms")
        self.generate_button.setMinimumHeight(35)
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self._on_generate_clicked)
        layout.addWidget(self.generate_button, 3, 0, 1, 2)
        
        group.setLayout(layout)
        return group
    
    def _create_spectrogram_display(self) -> QGroupBox:
        """Create spectrogram display group."""
        group = QGroupBox("Spectrogram Display")
        layout = QVBoxLayout()
        
        # Segment info
        self.segment_info_label = QLabel("No segments generated")
        self.segment_info_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        self.segment_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.segment_info_label)
        
        # Spectrogram plot
        self.spectrogram_plot = pg.PlotWidget()
        self.spectrogram_plot.setMinimumHeight(400)
        self.spectrogram_plot.setLabel('left', 'Frequency', units='Hz', color='#e0e0e0', size='11pt')
        self.spectrogram_plot.setLabel('bottom', 'Time', units='s', color='#e0e0e0', size='11pt')
        self.spectrogram_plot.setBackground('#1a1f2e')
        layout.addWidget(self.spectrogram_plot)
        
        # Navigation controls
        nav_layout = QHBoxLayout()
        
        self.first_button = QPushButton("◄◄ First")
        self.first_button.setEnabled(False)
        self.first_button.clicked.connect(self._on_first_clicked)
        nav_layout.addWidget(self.first_button)
        
        self.prev_button = QPushButton("◄ Prev")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self._on_prev_clicked)
        nav_layout.addWidget(self.prev_button)
        
        self.segment_slider = QSlider(Qt.Orientation.Horizontal)
        self.segment_slider.setMinimum(0)
        self.segment_slider.setMaximum(0)
        self.segment_slider.setValue(0)
        self.segment_slider.setEnabled(False)
        self.segment_slider.valueChanged.connect(self._on_slider_changed)
        nav_layout.addWidget(self.segment_slider, stretch=1)
        
        self.next_button = QPushButton("Next ►")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self._on_next_clicked)
        nav_layout.addWidget(self.next_button)
        
        self.last_button = QPushButton("Last ►►")
        self.last_button.setEnabled(False)
        self.last_button.clicked.connect(self._on_last_clicked)
        nav_layout.addWidget(self.last_button)
        
        layout.addLayout(nav_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_spectrogram_parameters(self) -> QGroupBox:
        """Create spectrogram parameters group."""
        group = QGroupBox("Spectrogram Parameters")
        layout = QGridLayout()
        
        # NFFT
        layout.addWidget(QLabel("NFFT:"), 0, 0)
        self.nfft_spin = QSpinBox()
        self.nfft_spin.setMinimum(128)
        self.nfft_spin.setMaximum(65536)
        self.nfft_spin.setValue(2048)
        self.nfft_spin.setSingleStep(128)
        layout.addWidget(self.nfft_spin, 0, 1)
        
        # Overlap
        layout.addWidget(QLabel("Overlap:"), 0, 2)
        self.spec_overlap_spin = QSpinBox()
        self.spec_overlap_spin.setMinimum(0)
        self.spec_overlap_spin.setMaximum(99)
        self.spec_overlap_spin.setValue(75)
        self.spec_overlap_spin.setSuffix(" %")
        layout.addWidget(self.spec_overlap_spin, 0, 3)
        
        # Window function
        layout.addWidget(QLabel("Window:"), 1, 0)
        self.window_combo = QComboBox()
        self.window_combo.addItems(['hann', 'hamming', 'blackman', 'bartlett'])
        layout.addWidget(self.window_combo, 1, 1)
        
        # Frequency range
        layout.addWidget(QLabel("Freq Range:"), 1, 2)
        freq_range_layout = QHBoxLayout()
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setMinimum(0)
        self.freq_min_spin.setMaximum(1000000)
        self.freq_min_spin.setValue(0)
        self.freq_min_spin.setSuffix(" Hz")
        freq_range_layout.addWidget(self.freq_min_spin)
        
        freq_range_layout.addWidget(QLabel("-"))
        
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setMinimum(0)
        self.freq_max_spin.setMaximum(1000000)
        self.freq_max_spin.setValue(25000)
        self.freq_max_spin.setSuffix(" Hz")
        freq_range_layout.addWidget(self.freq_max_spin)
        
        layout.addLayout(freq_range_layout, 1, 3)
        
        # Update buttons
        button_layout = QHBoxLayout()
        
        self.update_current_button = QPushButton("Update Current Segment")
        self.update_current_button.setEnabled(False)
        self.update_current_button.clicked.connect(self._on_update_current_clicked)
        button_layout.addWidget(self.update_current_button)
        
        self.update_all_button = QPushButton("Update All Segments")
        self.update_all_button.setEnabled(False)
        self.update_all_button.clicked.connect(self._on_update_all_clicked)
        button_layout.addWidget(self.update_all_button)
        
        layout.addLayout(button_layout, 2, 0, 1, 4)
        
        group.setLayout(layout)
        return group
    
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
                margin-top: 10px;
                padding-top: 10px;
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
                padding: 8px 16px;
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
                padding: 6px;
                color: #e0e0e0;
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
    
    # Event handlers
    
    def _on_browse_file_clicked(self):
        """Handle browse file button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select HDF5 File", "", "HDF5 Files (*.h5 *.hdf5);;All Files (*)"
        )
        
        if file_path:
            self._load_hdf5_file(file_path)
    
    def _load_hdf5_file(self, file_path: str):
        """Load HDF5 file and populate flight/channel lists."""
        try:
            self.hdf5_loader = HDF5FlightDataLoader(file_path)
            
            # Update file path display
            self.file_path_edit.setText(file_path)
            
            # Get file info
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            self.file_info_label.setText(f"Size: {file_size_mb:.1f} MB")
            self.file_info_label.setStyleSheet("color: #60a5fa;")
            
            # Populate flight combo
            flights = self.hdf5_loader.get_flight_list()
            self.flight_combo.clear()
            self.flight_combo.addItems(flights)
            self.flight_combo.setEnabled(True)
            
        except Exception as e:
            show_critical(self, "Error Loading File", f"Failed to load HDF5 file:\n\n{str(e)}")
            self.file_info_label.setText("Error loading file")
            self.file_info_label.setStyleSheet("color: #ef4444;")
    
    def _on_flight_changed(self):
        """Handle flight selection change."""
        flight_key = self.flight_combo.currentText()
        if not flight_key or not self.hdf5_loader:
            return
        
        try:
            # Get channels for this flight
            channels = self.hdf5_loader.get_channel_list(flight_key)
            
            # Populate channel combo
            self.channel_combo.clear()
            self.channel_combo.addItems(channels)
            self.channel_combo.setEnabled(True)
            
        except Exception as e:
            show_critical(self, "Error", f"Failed to load flight channels:\n\n{str(e)}")
    
    def _on_channel_changed(self):
        """Handle channel selection change."""
        channel_name = self.channel_combo.currentText()
        flight_key = self.flight_combo.currentText()
        
        if not channel_name or not flight_key or not self.hdf5_loader:
            return
        
        try:
            # Load channel data
            data_dict = self.hdf5_loader.load_channel_data(
                flight_key, channel_name,
                decimate=False,  # Always use full resolution
                max_points=None
            )
            
            self.signal_data = data_dict['data']
            self.sample_rate = data_dict['sample_rate']
            self.channel_name = channel_name
            self.flight_key = flight_key
            
            # Update UI
            duration = len(self.signal_data) / self.sample_rate
            self.file_info_label.setText(
                f"Size: {os.path.getsize(self.file_path_edit.text()) / (1024 * 1024):.1f} MB | "
                f"Duration: {duration:.1f}s | "
                f"Sample Rate: {self.sample_rate:.0f} Hz"
            )
            
            # Enable segmentation controls
            self.segment_duration_spin.setEnabled(True)
            self.segment_overlap_spin.setEnabled(True)
            self.generate_button.setEnabled(True)
            
            # Update frequency range max
            nyquist = self.sample_rate / 2
            self.freq_max_spin.setMaximum(nyquist)
            self.freq_max_spin.setValue(min(nyquist, 25000))
            
        except Exception as e:
            show_critical(self, "Error", f"Failed to load channel data:\n\n{str(e)}")
    
    def _on_generate_clicked(self):
        """Handle generate spectrograms button click."""
        if self.signal_data is None:
            return
        
        # Calculate segments
        segment_duration = self.segment_duration_spin.value()
        overlap_pct = self.segment_overlap_spin.value()
        
        segment_samples = int(segment_duration * self.sample_rate)
        overlap_samples = int(segment_samples * overlap_pct / 100)
        step_samples = segment_samples - overlap_samples
        
        total_samples = len(self.signal_data)
        
        # Generate segment boundaries
        self.segments = []
        start_idx = 0
        
        while start_idx < total_samples:
            end_idx = min(start_idx + segment_samples, total_samples)
            self.segments.append((start_idx, end_idx))
            
            if end_idx >= total_samples:
                break
            
            start_idx += step_samples
        
        # Update UI
        self.total_segments_label.setText(f"Total Segments: {len(self.segments)}")
        self.current_segment_idx = 0
        
        # Enable navigation
        self.segment_slider.setMaximum(len(self.segments) - 1)
        self.segment_slider.setValue(0)
        self.segment_slider.setEnabled(True)
        self.first_button.setEnabled(True)
        self.prev_button.setEnabled(True)
        self.next_button.setEnabled(True)
        self.last_button.setEnabled(True)
        self.update_current_button.setEnabled(True)
        self.update_all_button.setEnabled(True)
        self.export_current_button.setEnabled(True)
        self.export_all_button.setEnabled(True)
        
        # Clear cache
        self.spectrogram_cache.clear()
        
        # Display first segment
        self._display_segment(0)
    
    def _display_segment(self, segment_idx: int):
        """Display spectrogram for the given segment."""
        if segment_idx < 0 or segment_idx >= len(self.segments):
            return
        
        self.current_segment_idx = segment_idx
        
        # Update segment info
        start_idx, end_idx = self.segments[segment_idx]
        start_time = start_idx / self.sample_rate
        end_time = end_idx / self.sample_rate
        duration = (end_idx - start_idx) / self.sample_rate
        
        self.segment_info_label.setText(
            f"Segment {segment_idx + 1} of {len(self.segments)} | "
            f"Time: {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s)"
        )
        self.segment_info_label.setStyleSheet("color: #60a5fa; font-weight: bold;")
        
        # Check cache
        cached_spec = self.spectrogram_cache.get(segment_idx)
        
        if cached_spec is not None:
            # Use cached spectrogram
            f, t, Sxx = cached_spec
            self._plot_spectrogram(f, t, Sxx, start_time)
        else:
            # Generate new spectrogram
            segment_data = self.signal_data[start_idx:end_idx]
            
            nfft = self.nfft_spin.value()
            overlap_pct = self.spec_overlap_spin.value()
            window = self.window_combo.currentText()
            
            # Generate in background thread
            self.generator_thread = SpectrogramGenerator(
                segment_data, self.sample_rate, nfft, overlap_pct, window
            )
            self.generator_thread.segment_idx = segment_idx
            self.generator_thread.generation_complete.connect(self._on_spectrogram_generated)
            self.generator_thread.generation_error.connect(self._on_generation_error)
            self.generator_thread.start()
            
            # Show loading message
            self.segment_info_label.setText(
                f"Generating spectrogram for segment {segment_idx + 1}..."
            )
    
    def _on_spectrogram_generated(self, segment_idx: int, spectrogram_data):
        """Handle spectrogram generation completion."""
        f, t, Sxx = spectrogram_data
        
        # Cache the spectrogram
        self.spectrogram_cache.put(segment_idx, (f, t, Sxx))
        
        # Plot if this is still the current segment
        if segment_idx == self.current_segment_idx:
            start_idx, _ = self.segments[segment_idx]
            start_time = start_idx / self.sample_rate
            self._plot_spectrogram(f, t, Sxx, start_time)
    
    def _on_generation_error(self, error_msg: str):
        """Handle spectrogram generation error."""
        show_critical(self, "Generation Error", f"Failed to generate spectrogram:\n\n{error_msg}")
    
    def _plot_spectrogram(self, f: np.ndarray, t: np.ndarray, Sxx: np.ndarray, start_time: float):
        """Plot spectrogram on the display."""
        # Apply frequency range filter
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        freq_mask = (f >= freq_min) & (f <= freq_max)
        f_filtered = f[freq_mask]
        Sxx_filtered = Sxx[freq_mask, :]
        
        # Convert to dB
        Sxx_db = 10 * np.log10(Sxx_filtered + 1e-10)
        
        # Clear previous plot
        self.spectrogram_plot.clear()
        
        # Create image item
        img = pg.ImageItem()
        img.setImage(Sxx_db.T)  # Transpose for correct orientation
        
        # Set position and scale
        img.setRect(pg.QtCore.QRectF(
            start_time + t[0],  # x position
            f_filtered[0],  # y position
            t[-1] - t[0],  # width (time range)
            f_filtered[-1] - f_filtered[0]  # height (frequency range)
        ))
        
        # Set colormap
        img.setLookupTable(pg.colormap.get('viridis').getLookupTable())
        
        # Add to plot
        self.spectrogram_plot.addItem(img)
        
        # Update axes
        self.spectrogram_plot.setXRange(start_time + t[0], start_time + t[-1])
        self.spectrogram_plot.setYRange(f_filtered[0], f_filtered[-1])
        
        # Add colorbar (if not already present)
        # Note: pyqtgraph doesn't have built-in colorbar, would need custom implementation
    
    def _on_first_clicked(self):
        """Navigate to first segment."""
        self.segment_slider.setValue(0)
    
    def _on_prev_clicked(self):
        """Navigate to previous segment."""
        if self.current_segment_idx > 0:
            self.segment_slider.setValue(self.current_segment_idx - 1)
    
    def _on_next_clicked(self):
        """Navigate to next segment."""
        if self.current_segment_idx < len(self.segments) - 1:
            self.segment_slider.setValue(self.current_segment_idx + 1)
    
    def _on_last_clicked(self):
        """Navigate to last segment."""
        self.segment_slider.setValue(len(self.segments) - 1)
    
    def _on_slider_changed(self, value: int):
        """Handle slider value change."""
        self._display_segment(value)
    
    def _on_update_current_clicked(self):
        """Regenerate current segment with new parameters."""
        # Remove from cache
        if self.current_segment_idx in self.spectrogram_cache.cache:
            del self.spectrogram_cache.cache[self.current_segment_idx]
        
        # Regenerate
        self._display_segment(self.current_segment_idx)
    
    def _on_update_all_clicked(self):
        """Regenerate all segments with new parameters."""
        # Clear cache
        self.spectrogram_cache.clear()
        
        # Regenerate current segment
        self._display_segment(self.current_segment_idx)
        
        show_information(
            self,
            "Cache Cleared",
            "Spectrogram cache has been cleared. Segments will be regenerated "
            "with new parameters as you navigate through them."
        )
    
    def _on_export_current_clicked(self):
        """Export current segment spectrogram."""
        if self.current_segment_idx >= len(self.segments):
            return
        
        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Spectrogram", "", "PNG Image (*.png);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Ensure .png extension
        if not file_path.endswith('.png'):
            file_path += '.png'
        
        try:
            # Export using pyqtgraph's export functionality
            exporter = pg.exporters.ImageExporter(self.spectrogram_plot.plotItem)
            exporter.export(file_path)
            
            show_information(self, "Export Complete", f"Spectrogram saved to:\n{file_path}")
        
        except Exception as e:
            show_critical(self, "Export Error", f"Failed to export spectrogram:\n\n{str(e)}")
    
    def _on_export_all_clicked(self):
        """Export all segment spectrograms."""
        # Get output directory
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for All Spectrograms"
        )
        
        if not output_dir:
            return
        
        # Create progress dialog
        progress = QProgressDialog(
            "Exporting spectrograms...", "Cancel", 0, len(self.segments), self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        
        try:
            for i in range(len(self.segments)):
                if progress.wasCanceled():
                    break
                
                progress.setValue(i)
                progress.setLabelText(f"Exporting segment {i + 1} of {len(self.segments)}...")
                
                # Generate spectrogram if not cached
                if self.spectrogram_cache.get(i) is None:
                    start_idx, end_idx = self.segments[i]
                    segment_data = self.signal_data[start_idx:end_idx]
                    
                    nfft = self.nfft_spin.value()
                    overlap_pct = self.spec_overlap_spin.value()
                    window = self.window_combo.currentText()
                    noverlap = int(nfft * overlap_pct / 100)
                    
                    f, t, Sxx = signal.spectrogram(
                        segment_data,
                        fs=self.sample_rate,
                        window=window,
                        nperseg=nfft,
                        noverlap=noverlap,
                        scaling='density'
                    )
                    
                    self.spectrogram_cache.put(i, (f, t, Sxx))
                
                # Display and export
                self._display_segment(i)
                
                # Give UI time to update
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                
                # Export
                file_path = os.path.join(output_dir, f"spectrogram_segment_{i+1:03d}.png")
                exporter = pg.exporters.ImageExporter(self.spectrogram_plot.plotItem)
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
