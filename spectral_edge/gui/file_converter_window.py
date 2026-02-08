"""
File Format Conversion Tool GUI

This module provides a graphical user interface for converting between different
file formats used in signal processing and vibration analysis.

Supported conversions:
- DXD to CSV/HDF5 (with time slicing and splitting)
- HDF5 splitting by count or time slices
- Future: MATLAB to HDF5

Key Features:
- Memory-efficient chunked processing for large files
- Real-time progress tracking
- Background threading (non-blocking GUI)
- File size estimation before conversion
- SpectralEdge-compatible HDF5 output

Author: SpectralEdge Development Team
Date: 2026-02-08
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QGridLayout, QMessageBox, QCheckBox, QRadioButton,
    QProgressBar, QTextEdit, QScrollArea, QButtonGroup, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Import backend conversion functions
from spectral_edge.utils.file_converter import (
    get_dxd_file_info,
    convert_dxd_to_format,
    convert_dxd_with_splitting,
    split_hdf5_by_count,
    split_hdf5_by_time_slices
)
from spectral_edge.utils.message_box import show_information, show_warning, show_critical


class ConversionWorker(QThread):
    """
    Background worker thread for file conversion operations.
    
    This thread runs conversion operations in the background to keep the GUI responsive.
    Emits signals to update progress and report completion/errors.
    """
    
    progress_updated = pyqtSignal(int, str)  # (percentage, message)
    conversion_complete = pyqtSignal(list)  # list of output file paths
    conversion_error = pyqtSignal(str)  # error message
    
    def __init__(self, conversion_func, *args, **kwargs):
        """
        Initialize conversion worker.
        
        Parameters
        ----------
        conversion_func : callable
            The conversion function to run (e.g., convert_dxd_with_splitting)
        *args
            Positional arguments to pass to conversion function
        **kwargs
            Keyword arguments to pass to conversion function
        """
        super().__init__()
        self.conversion_func = conversion_func
        self.args = args
        self.kwargs = kwargs
        self.kwargs['progress_callback'] = self._progress_callback
    
    def _progress_callback(self, percentage: int, message: str):
        """Internal callback to emit progress signals."""
        self.progress_updated.emit(percentage, message)
    
    def run(self):
        """Run the conversion in background thread."""
        try:
            result = self.conversion_func(*self.args, **self.kwargs)
            self.conversion_complete.emit(result if isinstance(result, list) else [result])
        except Exception as e:
            self.conversion_error.emit(str(e))


class FileConverterWindow(QMainWindow):
    """
    Main window for File Format Conversion Tool.
    
    Provides GUI for converting between DXD, CSV, HDF5, and MATLAB formats
    with support for time slicing and file splitting.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Format Conversion Tool")
        self.setMinimumSize(900, 800)
        
        # State variables
        self.input_file_path = None
        self.file_info = None
        self.conversion_worker = None
        self.time_slices = []  # List of (start, end) tuples for custom slicing
        
        # Create UI
        self._create_ui()
        
        # Apply dark theme styling
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
        title_label = QLabel("File Format Conversion Tool")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Conversion mode selection
        mode_group = self._create_mode_selection()
        main_layout.addWidget(mode_group)
        
        # Input file selection
        input_group = self._create_input_selection()
        main_layout.addWidget(input_group)
        
        # Output settings
        output_group = self._create_output_settings()
        main_layout.addWidget(output_group)
        
        # Splitting options (for DXD mode)
        self.splitting_group = self._create_splitting_options()
        main_layout.addWidget(self.splitting_group)
        
        # HDF5 splitting options (for HDF5 mode)
        self.hdf5_split_group = self._create_hdf5_splitting_options()
        main_layout.addWidget(self.hdf5_split_group)
        self.hdf5_split_group.setVisible(False)
        
        # Channel selection (for DXD mode)
        self.channel_group = self._create_channel_selection()
        main_layout.addWidget(self.channel_group)
        
        # Progress section
        progress_group = self._create_progress_section()
        main_layout.addWidget(progress_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.convert_button = QPushButton("Convert")
        self.convert_button.setMinimumWidth(120)
        self.convert_button.setMinimumHeight(35)
        self.convert_button.clicked.connect(self._on_convert_clicked)
        self.convert_button.setEnabled(False)
        button_layout.addWidget(self.convert_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(120)
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        close_button = QPushButton("Close")
        close_button.setMinimumWidth(120)
        close_button.setMinimumHeight(35)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
        
        # Add stretch at bottom
        main_layout.addStretch()
    
    def _create_mode_selection(self) -> QGroupBox:
        """Create conversion mode selection group."""
        group = QGroupBox("Conversion Mode")
        layout = QVBoxLayout()
        
        self.mode_button_group = QButtonGroup()
        
        self.dxd_mode_radio = QRadioButton("DXD to CSV/HDF5")
        self.dxd_mode_radio.setChecked(True)
        self.dxd_mode_radio.toggled.connect(self._on_mode_changed)
        self.mode_button_group.addButton(self.dxd_mode_radio)
        layout.addWidget(self.dxd_mode_radio)
        
        self.hdf5_split_mode_radio = QRadioButton("HDF5 Splitting")
        self.hdf5_split_mode_radio.toggled.connect(self._on_mode_changed)
        self.mode_button_group.addButton(self.hdf5_split_mode_radio)
        layout.addWidget(self.hdf5_split_mode_radio)
        
        self.matlab_mode_radio = QRadioButton("MATLAB to HDF5 (Coming Soon)")
        self.matlab_mode_radio.setEnabled(False)
        self.mode_button_group.addButton(self.matlab_mode_radio)
        layout.addWidget(self.matlab_mode_radio)
        
        group.setLayout(layout)
        return group
    
    def _create_input_selection(self) -> QGroupBox:
        """Create input file selection group."""
        group = QGroupBox("Input File")
        layout = QVBoxLayout()
        
        # File path selection
        file_layout = QHBoxLayout()
        
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Select input file...")
        self.input_path_edit.setReadOnly(True)
        file_layout.addWidget(self.input_path_edit)
        
        browse_button = QPushButton("Browse")
        browse_button.setMinimumWidth(100)
        browse_button.clicked.connect(self._on_browse_input_clicked)
        file_layout.addWidget(browse_button)
        
        layout.addLayout(file_layout)
        
        # File info display
        self.file_info_label = QLabel("No file selected")
        self.file_info_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        layout.addWidget(self.file_info_label)
        
        group.setLayout(layout)
        return group
    
    def _create_output_settings(self) -> QGroupBox:
        """Create output settings group."""
        group = QGroupBox("Output Settings")
        layout = QGridLayout()
        
        # Output format selection
        layout.addWidget(QLabel("Format:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["HDF5", "CSV"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        layout.addWidget(self.format_combo, 0, 1)
        
        # Output path/directory
        layout.addWidget(QLabel("Output:"), 1, 0)
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Select output location...")
        layout.addWidget(self.output_path_edit, 1, 1)
        
        self.output_browse_button = QPushButton("Browse")
        self.output_browse_button.setMinimumWidth(100)
        self.output_browse_button.clicked.connect(self._on_browse_output_clicked)
        layout.addWidget(self.output_browse_button, 1, 2)
        
        # Size estimate
        self.size_estimate_label = QLabel("")
        self.size_estimate_label.setStyleSheet("color: #60a5fa; font-weight: bold;")
        layout.addWidget(self.size_estimate_label, 2, 0, 1, 3)
        
        group.setLayout(layout)
        return group
    
    def _create_splitting_options(self) -> QGroupBox:
        """Create DXD splitting options group."""
        group = QGroupBox("Splitting Options")
        layout = QVBoxLayout()
        
        # Splitting mode selection
        self.split_button_group = QButtonGroup()
        
        self.no_split_radio = QRadioButton("Single file (no splitting)")
        self.no_split_radio.setChecked(True)
        self.no_split_radio.toggled.connect(self._on_split_mode_changed)
        self.split_button_group.addButton(self.no_split_radio)
        layout.addWidget(self.no_split_radio)
        
        # Split by count
        count_layout = QHBoxLayout()
        self.split_count_radio = QRadioButton("Split by count:")
        self.split_count_radio.toggled.connect(self._on_split_mode_changed)
        self.split_button_group.addButton(self.split_count_radio)
        count_layout.addWidget(self.split_count_radio)
        
        self.segment_count_spin = QSpinBox()
        self.segment_count_spin.setMinimum(2)
        self.segment_count_spin.setMaximum(1000)
        self.segment_count_spin.setValue(10)
        self.segment_count_spin.setSuffix(" segments")
        self.segment_count_spin.setEnabled(False)
        self.segment_count_spin.valueChanged.connect(self._update_segment_preview)
        count_layout.addWidget(self.segment_count_spin)
        
        self.segment_preview_label = QLabel("")
        self.segment_preview_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        count_layout.addWidget(self.segment_preview_label)
        count_layout.addStretch()
        
        layout.addLayout(count_layout)
        
        # Split by time slices
        self.split_slices_radio = QRadioButton("Split by time slices")
        self.split_slices_radio.toggled.connect(self._on_split_mode_changed)
        self.split_button_group.addButton(self.split_slices_radio)
        layout.addWidget(self.split_slices_radio)
        
        # Time slices table
        slices_layout = QHBoxLayout()
        slices_layout.addSpacing(30)  # Indent
        
        slices_container = QWidget()
        slices_vlayout = QVBoxLayout(slices_container)
        slices_vlayout.setContentsMargins(0, 0, 0, 0)
        
        # Buttons for managing slices
        slice_buttons_layout = QHBoxLayout()
        
        self.add_slice_button = QPushButton("Add Slice")
        self.add_slice_button.setEnabled(False)
        self.add_slice_button.clicked.connect(self._on_add_slice_clicked)
        slice_buttons_layout.addWidget(self.add_slice_button)
        
        self.remove_slice_button = QPushButton("Remove Slice")
        self.remove_slice_button.setEnabled(False)
        self.remove_slice_button.clicked.connect(self._on_remove_slice_clicked)
        slice_buttons_layout.addWidget(self.remove_slice_button)
        
        self.auto_divide_button = QPushButton("Auto-Divide")
        self.auto_divide_button.setEnabled(False)
        self.auto_divide_button.clicked.connect(self._on_auto_divide_clicked)
        slice_buttons_layout.addWidget(self.auto_divide_button)
        
        slice_buttons_layout.addStretch()
        slices_vlayout.addLayout(slice_buttons_layout)
        
        # Table for time slices
        self.slices_table = QTableWidget()
        self.slices_table.setColumnCount(3)
        self.slices_table.setHorizontalHeaderLabels(["Start (s)", "End (s)", "Duration (s)"])
        self.slices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.slices_table.setMaximumHeight(150)
        self.slices_table.setEnabled(False)
        slices_vlayout.addWidget(self.slices_table)
        
        slices_layout.addWidget(slices_container)
        layout.addLayout(slices_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_hdf5_splitting_options(self) -> QGroupBox:
        """Create HDF5 splitting options group."""
        group = QGroupBox("HDF5 Splitting Options")
        layout = QVBoxLayout()
        
        # Splitting mode selection
        self.hdf5_split_button_group = QButtonGroup()
        
        # Split by count
        count_layout = QHBoxLayout()
        self.hdf5_split_count_radio = QRadioButton("Split into:")
        self.hdf5_split_count_radio.setChecked(True)
        self.hdf5_split_button_group.addButton(self.hdf5_split_count_radio)
        count_layout.addWidget(self.hdf5_split_count_radio)
        
        self.hdf5_segment_count_spin = QSpinBox()
        self.hdf5_segment_count_spin.setMinimum(2)
        self.hdf5_segment_count_spin.setMaximum(1000)
        self.hdf5_segment_count_spin.setValue(10)
        self.hdf5_segment_count_spin.setSuffix(" equal segments")
        count_layout.addWidget(self.hdf5_segment_count_spin)
        count_layout.addStretch()
        
        layout.addLayout(count_layout)
        
        # Split by time slices
        self.hdf5_split_slices_radio = QRadioButton("Split by time slices:")
        self.hdf5_split_button_group.addButton(self.hdf5_split_slices_radio)
        layout.addWidget(self.hdf5_split_slices_radio)
        
        # Time slices table (similar to DXD mode)
        slices_layout = QHBoxLayout()
        slices_layout.addSpacing(30)
        
        slices_container = QWidget()
        slices_vlayout = QVBoxLayout(slices_container)
        slices_vlayout.setContentsMargins(0, 0, 0, 0)
        
        slice_buttons_layout = QHBoxLayout()
        
        self.hdf5_add_slice_button = QPushButton("Add Slice")
        self.hdf5_add_slice_button.clicked.connect(self._on_hdf5_add_slice_clicked)
        slice_buttons_layout.addWidget(self.hdf5_add_slice_button)
        
        self.hdf5_remove_slice_button = QPushButton("Remove Slice")
        self.hdf5_remove_slice_button.clicked.connect(self._on_hdf5_remove_slice_clicked)
        slice_buttons_layout.addWidget(self.hdf5_remove_slice_button)
        
        slice_buttons_layout.addStretch()
        slices_vlayout.addLayout(slice_buttons_layout)
        
        self.hdf5_slices_table = QTableWidget()
        self.hdf5_slices_table.setColumnCount(3)
        self.hdf5_slices_table.setHorizontalHeaderLabels(["Start (s)", "End (s)", "Duration (s)"])
        self.hdf5_slices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.hdf5_slices_table.setMaximumHeight(150)
        slices_vlayout.addWidget(self.hdf5_slices_table)
        
        slices_layout.addWidget(slices_container)
        layout.addLayout(slices_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_channel_selection(self) -> QGroupBox:
        """Create channel selection group."""
        group = QGroupBox("Channel Selection (Optional)")
        layout = QVBoxLayout()
        
        self.select_channels_checkbox = QCheckBox("Select specific channels")
        self.select_channels_checkbox.setChecked(False)
        self.select_channels_checkbox.toggled.connect(self._on_select_channels_toggled)
        layout.addWidget(self.select_channels_checkbox)
        
        self.channels_button = QPushButton("Select Channels...")
        self.channels_button.setEnabled(False)
        self.channels_button.clicked.connect(self._on_select_channels_clicked)
        layout.addWidget(self.channels_button)
        
        self.selected_channels_label = QLabel("All channels will be included")
        self.selected_channels_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        layout.addWidget(self.selected_channels_label)
        
        group.setLayout(layout)
        return group
    
    def _create_progress_section(self) -> QGroupBox:
        """Create progress tracking section."""
        group = QGroupBox("Progress")
        layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Status message
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #9ca3af;")
        layout.addWidget(self.status_label)
        
        # Output files list
        self.output_files_text = QTextEdit()
        self.output_files_text.setReadOnly(True)
        self.output_files_text.setMaximumHeight(100)
        self.output_files_text.setPlaceholderText("Output files will be listed here...")
        layout.addWidget(self.output_files_text)
        
        group.setLayout(layout)
        return group
    
    def _apply_styling(self):
        """Apply dark theme styling to the window."""
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
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border: 1px solid #60a5fa;
            }
            QProgressBar {
                border: 1px solid #4a5568;
                border-radius: 4px;
                background-color: #2d3748;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 4px;
                color: #e0e0e0;
            }
            QTableWidget {
                background-color: #2d3748;
                border: 1px solid #4a5568;
                gridline-color: #4a5568;
                color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #374151;
                color: #e0e0e0;
                padding: 5px;
                border: 1px solid #4a5568;
                font-weight: bold;
            }
            QRadioButton, QCheckBox {
                color: #e0e0e0;
                spacing: 5px;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton::indicator::unchecked, QCheckBox::indicator::unchecked {
                border: 2px solid #4a5568;
                background-color: #2d3748;
                border-radius: 9px;
            }
            QRadioButton::indicator::checked, QCheckBox::indicator::checked {
                border: 2px solid #3b82f6;
                background-color: #3b82f6;
                border-radius: 9px;
            }
        """)
    
    # Event handlers
    
    def _on_mode_changed(self):
        """Handle conversion mode change."""
        is_dxd_mode = self.dxd_mode_radio.isChecked()
        is_hdf5_mode = self.hdf5_split_mode_radio.isChecked()
        
        # Show/hide relevant groups
        self.splitting_group.setVisible(is_dxd_mode)
        self.channel_group.setVisible(is_dxd_mode)
        self.hdf5_split_group.setVisible(is_hdf5_mode)
        
        # Update format combo
        if is_hdf5_mode:
            self.format_combo.setEnabled(False)
            self.format_combo.setCurrentText("HDF5")
        else:
            self.format_combo.setEnabled(True)
        
        # Clear file info
        self.input_file_path = None
        self.file_info = None
        self.input_path_edit.clear()
        self.file_info_label.setText("No file selected")
        self._update_convert_button_state()
    
    def _on_browse_input_clicked(self):
        """Handle browse input file button click."""
        if self.dxd_mode_radio.isChecked():
            file_filter = "DXD Files (*.dxd *.dxz);;All Files (*)"
            title = "Select DXD File"
        else:  # HDF5 mode
            file_filter = "HDF5 Files (*.h5 *.hdf5);;All Files (*)"
            title = "Select HDF5 File"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, "", file_filter
        )
        
        if file_path:
            self.input_file_path = file_path
            self.input_path_edit.setText(file_path)
            self._load_file_info()
    
    def _load_file_info(self):
        """Load and display file information."""
        if not self.input_file_path:
            return
        
        try:
            if self.dxd_mode_radio.isChecked():
                # Load DXD file info
                self.file_info = get_dxd_file_info(self.input_file_path)
                
                # Display info
                duration = self.file_info['duration']
                num_channels = len(self.file_info['channels'])
                file_size_mb = self.file_info['file_size'] / (1024 * 1024)
                
                info_text = (
                    f"Duration: {duration:.2f}s | "
                    f"Channels: {num_channels} | "
                    f"Size: {file_size_mb:.1f} MB"
                )
                self.file_info_label.setText(info_text)
                self.file_info_label.setStyleSheet("color: #60a5fa;")
                
                # Update segment preview if split by count is selected
                self._update_segment_preview()
                
            else:  # HDF5 mode
                # For HDF5, just show file size for now
                file_size_mb = os.path.getsize(self.input_file_path) / (1024 * 1024)
                self.file_info_label.setText(f"Size: {file_size_mb:.1f} MB")
                self.file_info_label.setStyleSheet("color: #60a5fa;")
            
            self._update_convert_button_state()
            
        except Exception as e:
            show_critical(self, "Error Loading File", f"Failed to load file information:\n\n{str(e)}")
            self.input_file_path = None
            self.file_info = None
            self.file_info_label.setText("Error loading file")
            self.file_info_label.setStyleSheet("color: #ef4444;")
    
    def _on_browse_output_clicked(self):
        """Handle browse output location button click."""
        # Determine if we need directory or file
        is_splitting = (
            (self.dxd_mode_radio.isChecked() and not self.no_split_radio.isChecked()) or
            self.hdf5_split_mode_radio.isChecked()
        )
        
        if is_splitting:
            # Select directory for multiple output files
            dir_path = QFileDialog.getExistingDirectory(
                self, "Select Output Directory", ""
            )
            if dir_path:
                self.output_path_edit.setText(dir_path)
        else:
            # Select single output file
            format_text = self.format_combo.currentText().lower()
            if format_text == "hdf5":
                file_filter = "HDF5 Files (*.h5 *.hdf5);;All Files (*)"
                default_ext = ".h5"
            else:
                file_filter = "CSV Files (*.csv);;All Files (*)"
                default_ext = ".csv"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Select Output File", "", file_filter
            )
            
            if file_path:
                # Ensure correct extension
                if not file_path.endswith(default_ext):
                    file_path += default_ext
                self.output_path_edit.setText(file_path)
        
        self._update_convert_button_state()
        self._estimate_output_size()
    
    def _on_format_changed(self):
        """Handle output format change."""
        self._estimate_output_size()
    
    def _on_split_mode_changed(self):
        """Handle split mode change."""
        is_split_count = self.split_count_radio.isChecked()
        is_split_slices = self.split_slices_radio.isChecked()
        
        # Enable/disable controls
        self.segment_count_spin.setEnabled(is_split_count)
        self.add_slice_button.setEnabled(is_split_slices)
        self.remove_slice_button.setEnabled(is_split_slices)
        self.auto_divide_button.setEnabled(is_split_slices)
        self.slices_table.setEnabled(is_split_slices)
        
        # Update segment preview
        if is_split_count:
            self._update_segment_preview()
        else:
            self.segment_preview_label.setText("")
        
        # Update output browse button behavior
        self._estimate_output_size()
    
    def _update_segment_preview(self):
        """Update segment duration preview."""
        if not self.file_info or not self.split_count_radio.isChecked():
            self.segment_preview_label.setText("")
            return
        
        duration = self.file_info['duration']
        num_segments = self.segment_count_spin.value()
        segment_duration = duration / num_segments
        
        self.segment_preview_label.setText(
            f"→ Creates {num_segments} files, each {segment_duration:.1f}s"
        )
    
    def _on_add_slice_clicked(self):
        """Handle add time slice button click."""
        if not self.file_info:
            return
        
        # Add a new row to the table
        row = self.slices_table.rowCount()
        self.slices_table.insertRow(row)
        
        # Default values: start at end of previous slice or 0
        if row > 0:
            prev_end = float(self.slices_table.item(row - 1, 1).text())
            start = prev_end
        else:
            start = 0.0
        
        # End at file duration or 10s after start
        duration = self.file_info['duration']
        end = min(start + 10.0, duration)
        
        # Create editable items
        start_item = QTableWidgetItem(f"{start:.2f}")
        end_item = QTableWidgetItem(f"{end:.2f}")
        duration_item = QTableWidgetItem(f"{end - start:.2f}")
        duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
        
        self.slices_table.setItem(row, 0, start_item)
        self.slices_table.setItem(row, 1, end_item)
        self.slices_table.setItem(row, 2, duration_item)
        
        # Connect item changed signal
        self.slices_table.itemChanged.connect(self._on_slice_item_changed)
    
    def _on_remove_slice_clicked(self):
        """Handle remove time slice button click."""
        current_row = self.slices_table.currentRow()
        if current_row >= 0:
            self.slices_table.removeRow(current_row)
    
    def _on_auto_divide_clicked(self):
        """Handle auto-divide button click."""
        if not self.file_info:
            return
        
        # Ask user for number of slices
        from PyQt6.QtWidgets import QInputDialog
        
        num_slices, ok = QInputDialog.getInt(
            self, "Auto-Divide",
            "Number of equal time slices:",
            10, 2, 1000, 1
        )
        
        if not ok:
            return
        
        # Clear existing slices
        self.slices_table.setRowCount(0)
        
        # Create equal slices
        duration = self.file_info['duration']
        slice_duration = duration / num_slices
        
        for i in range(num_slices):
            start = i * slice_duration
            end = min((i + 1) * slice_duration, duration)
            
            row = self.slices_table.rowCount()
            self.slices_table.insertRow(row)
            
            start_item = QTableWidgetItem(f"{start:.2f}")
            end_item = QTableWidgetItem(f"{end:.2f}")
            duration_item = QTableWidgetItem(f"{end - start:.2f}")
            duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            self.slices_table.setItem(row, 0, start_item)
            self.slices_table.setItem(row, 1, end_item)
            self.slices_table.setItem(row, 2, duration_item)
    
    def _on_slice_item_changed(self, item):
        """Handle time slice table item change."""
        row = item.row()
        col = item.column()
        
        if col < 2:  # Start or end time changed
            try:
                start = float(self.slices_table.item(row, 0).text())
                end = float(self.slices_table.item(row, 1).text())
                duration = end - start
                
                # Update duration
                duration_item = self.slices_table.item(row, 2)
                if duration_item:
                    duration_item.setText(f"{duration:.2f}")
                
            except (ValueError, AttributeError):
                pass
    
    def _on_hdf5_add_slice_clicked(self):
        """Handle add HDF5 time slice button click."""
        # Similar to _on_add_slice_clicked but for HDF5 table
        row = self.hdf5_slices_table.rowCount()
        self.hdf5_slices_table.insertRow(row)
        
        start = row * 10.0  # Default 10s intervals
        end = (row + 1) * 10.0
        
        start_item = QTableWidgetItem(f"{start:.2f}")
        end_item = QTableWidgetItem(f"{end:.2f}")
        duration_item = QTableWidgetItem(f"{end - start:.2f}")
        duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        
        self.hdf5_slices_table.setItem(row, 0, start_item)
        self.hdf5_slices_table.setItem(row, 1, end_item)
        self.hdf5_slices_table.setItem(row, 2, duration_item)
    
    def _on_hdf5_remove_slice_clicked(self):
        """Handle remove HDF5 time slice button click."""
        current_row = self.hdf5_slices_table.currentRow()
        if current_row >= 0:
            self.hdf5_slices_table.removeRow(current_row)
    
    def _on_select_channels_toggled(self, checked):
        """Handle select channels checkbox toggle."""
        self.channels_button.setEnabled(checked)
        if not checked:
            self.selected_channels_label.setText("All channels will be included")
    
    def _on_select_channels_clicked(self):
        """Handle select channels button click."""
        if not self.file_info:
            return
        
        # Create channel selection dialog
        from PyQt6.QtWidgets import QDialog, QListWidget, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Channels")
        dialog.setMinimumSize(400, 500)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Select channels to include:"))
        
        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        for ch in self.file_info['channels']:
            list_widget.addItem(f"{ch['name']} ({ch['unit']})")
        
        # Select all by default
        for i in range(list_widget.count()):
            list_widget.item(i).setSelected(True)
        
        layout.addWidget(list_widget)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_items = list_widget.selectedItems()
            if selected_items:
                channel_names = [item.text().split(' (')[0] for item in selected_items]
                self.selected_channels = channel_names
                self.selected_channels_label.setText(
                    f"{len(channel_names)} channel(s) selected"
                )
            else:
                self.selected_channels = None
                self.selected_channels_label.setText("No channels selected (will include all)")
    
    def _estimate_output_size(self):
        """Estimate output file size."""
        if not self.file_info or not self.dxd_mode_radio.isChecked():
            self.size_estimate_label.setText("")
            return
        
        # Calculate total samples
        total_samples = 0
        for ch in self.file_info['channels']:
            total_samples += ch['sample_count']
        
        # Estimate size based on format
        format_text = self.format_combo.currentText().lower()
        if format_text == "csv":
            # CSV: ~10 bytes per value (text representation)
            estimated_bytes = total_samples * 10
        else:  # HDF5
            # HDF5: ~4 bytes per value (compressed double)
            estimated_bytes = total_samples * 4
        
        # Convert to human-readable
        if estimated_bytes < 1024 * 1024:
            size_str = f"{estimated_bytes / 1024:.1f} KB"
        elif estimated_bytes < 1024 * 1024 * 1024:
            size_str = f"{estimated_bytes / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{estimated_bytes / (1024 * 1024 * 1024):.2f} GB"
        
        self.size_estimate_label.setText(f"Estimated output size: {size_str}")
    
    def _update_convert_button_state(self):
        """Update convert button enabled state."""
        has_input = self.input_file_path is not None
        has_output = len(self.output_path_edit.text()) > 0
        
        self.convert_button.setEnabled(has_input and has_output)
    
    def _on_convert_clicked(self):
        """Handle convert button click."""
        # Validate inputs
        if not self.input_file_path or not self.output_path_edit.text():
            show_warning(self, "Missing Information", "Please select input file and output location.")
            return
        
        # Disable UI during conversion
        self.convert_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting conversion...")
        self.output_files_text.clear()
        
        # Determine conversion mode and parameters
        if self.dxd_mode_radio.isChecked():
            self._start_dxd_conversion()
        elif self.hdf5_split_mode_radio.isChecked():
            self._start_hdf5_splitting()
    
    def _start_dxd_conversion(self):
        """Start DXD conversion in background thread."""
        output_format = self.format_combo.currentText().lower()
        
        # Get channels if selected
        channels = None
        if self.select_channels_checkbox.isChecked() and hasattr(self, 'selected_channels'):
            channels = self.selected_channels
        
        # Determine split mode
        if self.no_split_radio.isChecked():
            # Single file conversion
            output_path = self.output_path_edit.text()
            
            self.conversion_worker = ConversionWorker(
                convert_dxd_to_format,
                self.input_file_path,
                output_path,
                output_format,
                time_range=None,
                channels=channels
            )
        
        elif self.split_count_radio.isChecked():
            # Split by count
            output_dir = self.output_path_edit.text()
            num_segments = self.segment_count_spin.value()
            
            self.conversion_worker = ConversionWorker(
                convert_dxd_with_splitting,
                self.input_file_path,
                output_dir,
                output_format,
                split_mode='count',
                num_segments=num_segments,
                channels=channels
            )
        
        elif self.split_slices_radio.isChecked():
            # Split by time slices
            output_dir = self.output_path_edit.text()
            
            # Extract time slices from table
            time_slices = []
            for row in range(self.slices_table.rowCount()):
                try:
                    start = float(self.slices_table.item(row, 0).text())
                    end = float(self.slices_table.item(row, 1).text())
                    time_slices.append((start, end))
                except (ValueError, AttributeError):
                    show_warning(
                        self, "Invalid Time Slice",
                        f"Invalid time values in row {row + 1}. Please check your inputs."
                    )
                    self._reset_ui_after_conversion()
                    return
            
            if not time_slices:
                show_warning(self, "No Time Slices", "Please add at least one time slice.")
                self._reset_ui_after_conversion()
                return
            
            self.conversion_worker = ConversionWorker(
                convert_dxd_with_splitting,
                self.input_file_path,
                output_dir,
                output_format,
                split_mode='time_slices',
                time_slices=time_slices,
                channels=channels
            )
        
        # Connect signals
        self.conversion_worker.progress_updated.connect(self._on_progress_updated)
        self.conversion_worker.conversion_complete.connect(self._on_conversion_complete)
        self.conversion_worker.conversion_error.connect(self._on_conversion_error)
        
        # Start conversion
        self.conversion_worker.start()
    
    def _start_hdf5_splitting(self):
        """Start HDF5 splitting in background thread."""
        input_path = self.input_file_path
        output_dir = self.output_path_edit.text()
        
        if self.hdf5_split_count_radio.isChecked():
            # Split by count
            num_segments = self.hdf5_segment_count_spin.value()
            
            self.conversion_worker = ConversionWorker(
                split_hdf5_by_count,
                input_path,
                output_dir,
                num_segments
            )
        
        else:  # Split by time slices
            # Extract time slices from table
            time_slices = []
            for row in range(self.hdf5_slices_table.rowCount()):
                try:
                    start = float(self.hdf5_slices_table.item(row, 0).text())
                    end = float(self.hdf5_slices_table.item(row, 1).text())
                    time_slices.append((start, end))
                except (ValueError, AttributeError):
                    show_warning(
                        self, "Invalid Time Slice",
                        f"Invalid time values in row {row + 1}. Please check your inputs."
                    )
                    self._reset_ui_after_conversion()
                    return
            
            if not time_slices:
                show_warning(self, "No Time Slices", "Please add at least one time slice.")
                self._reset_ui_after_conversion()
                return
            
            self.conversion_worker = ConversionWorker(
                split_hdf5_by_time_slices,
                input_path,
                output_dir,
                time_slices
            )
        
        # Connect signals
        self.conversion_worker.progress_updated.connect(self._on_progress_updated)
        self.conversion_worker.conversion_complete.connect(self._on_conversion_complete)
        self.conversion_worker.conversion_error.connect(self._on_conversion_error)
        
        # Start conversion
        self.conversion_worker.start()
    
    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        if self.conversion_worker and self.conversion_worker.isRunning():
            # Terminate the worker thread
            self.conversion_worker.terminate()
            self.conversion_worker.wait()
            
            self.status_label.setText("Conversion cancelled")
            self.status_label.setStyleSheet("color: #f59e0b;")
            
            self._reset_ui_after_conversion()
    
    def _on_progress_updated(self, percentage: int, message: str):
        """Handle progress update from worker thread."""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #60a5fa;")
    
    def _on_conversion_complete(self, output_files: List[str]):
        """Handle conversion completion."""
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Conversion complete! Created {len(output_files)} file(s)")
        self.status_label.setStyleSheet("color: #10b981;")
        
        # Display output files
        self.output_files_text.clear()
        self.output_files_text.append("Output files:")
        for file_path in output_files:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            self.output_files_text.append(f"  • {file_path} ({file_size_mb:.1f} MB)")
        
        self._reset_ui_after_conversion()
        
        # Show success message
        show_information(
            self,
            "Conversion Complete",
            f"Successfully created {len(output_files)} file(s).\n\n"
            f"Output location: {os.path.dirname(output_files[0])}"
        )
    
    def _on_conversion_error(self, error_message: str):
        """Handle conversion error."""
        self.status_label.setText("Conversion failed")
        self.status_label.setStyleSheet("color: #ef4444;")
        
        self._reset_ui_after_conversion()
        
        show_critical(
            self,
            "Conversion Error",
            f"An error occurred during conversion:\n\n{error_message}"
        )
    
    def _reset_ui_after_conversion(self):
        """Reset UI state after conversion completes or is cancelled."""
        self.convert_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        # Clean up worker
        if self.conversion_worker:
            self.conversion_worker.deleteLater()
            self.conversion_worker = None
