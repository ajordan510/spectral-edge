"""
Enhanced Flight & Channel Navigator GUI

This module provides an advanced GUI for browsing and selecting flights and channels
from HDF5 files with search, filtering, multiple view modes, and customizable columns.

Features:
- Advanced search across channel names, locations, sensor IDs
- Multi-criteria filtering (sensor type, location)
- Multiple view modes (By Flight, By Location, By Sensor Type)
- Customizable columns (Name, Units, Sample Rate, Location, Time Range, etc.)
- Saved and recent selections
- Professional dark theme

Author: SpectralEdge Development Team
Date: 2026-01-27
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QGroupBox, QLineEdit,
    QCheckBox, QScrollArea, QWidget, QRadioButton, QComboBox,
    QMessageBox, QInputDialog, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QAction
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.utils.selection_manager import SelectionManager
from spectral_edge.utils.message_box import show_warning, show_information
from typing import List, Dict, Tuple, Optional
import re
from dataclasses import dataclass
from enum import Enum


class ViewMode(Enum):
    """Enumeration of available view modes"""
    BY_FLIGHT = "By Flight"
    BY_LOCATION = "By Location"
    BY_SENSOR_TYPE = "By Sensor Type"


@dataclass
class ColumnConfig:
    """Configuration for tree widget columns"""
    name: str
    title: str
    visible: bool
    width: int = 150


class FlightNavigator(QDialog):
    """
    Enhanced dialog for navigating and selecting flights and channels from HDF5 files.
    
    Features:
    - Search and filter functionality
    - Multiple view modes (Flight, Location, Sensor Type)
    - Customizable columns
    - Saved and recent selections
    
    Signals:
    --------
    data_selected : pyqtSignal
        Emitted when user clicks "Load Selected" with list of selected items
        Format: List[(flight_key, channel_key, channel_info)]
    """
    
    # Signal emitted when data is selected
    data_selected = pyqtSignal(object)
    
    def __init__(
        self,
        loader: HDF5FlightDataLoader,
        parent=None,
        max_selected_channels: Optional[int] = None,
        selection_limit_message: Optional[str] = None,
    ):
        """
        Initialize Enhanced Flight Navigator dialog.
        
        Parameters:
        -----------
        loader : HDF5FlightDataLoader
            Initialized HDF5 data loader with flight and channel data
        parent : QWidget, optional
            Parent widget for this dialog
        """
        super().__init__(parent)
        self.loader = loader
        self.selection_manager = SelectionManager()
        self.max_selected_channels = max_selected_channels
        self.selection_limit_message = selection_limit_message
        
        # Data storage
        self.selected_items = []  # List of (flight_key, channel_key, channel_info)
        self.all_channels = []  # All channels for filtering
        self.filtered_channels = []  # Channels after filtering
        
        # View mode
        self.current_view_mode = ViewMode.BY_FLIGHT
        
        # Column configuration (default visible: Name, Units, Sample Rate,
        # Location, Time Range, Sensor ID, Flight)
        self.columns = [
            ColumnConfig("name", "Channel Name", True, 200),
            ColumnConfig("units", "Units", True, 80),
            ColumnConfig("sample_rate", "Sample Rate", True, 100),
            ColumnConfig("location", "Location", True, 150),
            ColumnConfig("time_range", "Time Range", True, 120),
            ColumnConfig("sensor_id", "Sensor ID", True, 100),
            ColumnConfig("description", "Description", False, 200),
            ColumnConfig("range", "Range", False, 100),
            ColumnConfig("flight", "Flight", True, 100),
        ]
        
        # Search/filter state
        self.search_text = ""
        self.filter_sensor_types = set()
        self.filter_location = ""
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._apply_filters)
        
        # Window properties
        self.setWindowTitle("Enhanced Flight & Channel Navigator")
        self.setModal(False)
        self.resize(1200, 800)
        
        # Apply dark theme
        self._apply_styling()
        
        # Create UI
        self._create_ui()
        
        # Load data
        self._load_all_channels()
        self._populate_tree()
        
    def _apply_styling(self):
        """Apply professional dark theme styling to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1f2e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 10pt;
            }
            QGroupBox {
                color: #60a5fa;
                font-size: 11pt;
                font-weight: bold;
                border: 2px solid #4a5568;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTreeWidget#channelTree {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                font-size: 10pt;
            }
            QTreeWidget#channelTree::item:hover {
                background-color: #4a5568;
            }
            QTreeWidget#channelTree::item:selected {
                background-color: #3b82f6;
            }
            QTreeWidget#channelTree QHeaderView::section {
                background-color: #1a1f2e;
                color: #60a5fa;
                font-weight: bold;
                border: 1px solid #4a5568;
                padding: 4px;
            }
            QLineEdit {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                padding: 5px;
                border-radius: 3px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #60a5fa;
            }
            QComboBox {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                padding: 5px;
                border-radius: 3px;
                font-size: 10pt;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d3748;
                color: #e0e0e0;
                selection-background-color: #3b82f6;
            }
            QCheckBox {
                color: #e0e0e0;
                font-size: 10pt;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a5568;
                border-radius: 3px;
                background-color: #2d3748;
            }
            QCheckBox::indicator:checked {
                background-color: #3b82f6;
                border-color: #3b82f6;
            }
            QRadioButton {
                color: #e0e0e0;
                font-size: 10pt;
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a5568;
                border-radius: 9px;
                background-color: #2d3748;
            }
            QRadioButton::indicator:checked {
                background-color: #3b82f6;
                border-color: #3b82f6;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 10pt;
                border-radius: 4px;
                min-width: 80px;
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
            QPushButton#loadButton {
                background-color: #10b981;
                font-weight: bold;
            }
            QPushButton#loadButton:hover {
                background-color: #059669;
            }
        """)
    
    def _create_ui(self):
        """Create the user interface layout"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header with title and summary
        header_layout = QHBoxLayout()
        title_label = QLabel("Enhanced Flight & Channel Navigator")
        title_font = QFont("Arial", 14, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #60a5fa;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.summary_label = QLabel("0 channels selected")
        header_layout.addWidget(self.summary_label)
        main_layout.addLayout(header_layout)
        
        # Filter panel (collapsible)
        self.filter_group = self._create_filter_panel()
        main_layout.addWidget(self.filter_group)
        
        # View mode selection
        view_mode_layout = self._create_view_mode_panel()
        main_layout.addLayout(view_mode_layout)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setObjectName("channelTree")
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.itemChanged.connect(self._on_item_changed)
        self._apply_tree_header_styling()
        self._update_tree_columns()
        main_layout.addWidget(self.tree, stretch=1)
        
        # Bottom buttons
        button_layout = self._create_button_panel()
        main_layout.addLayout(button_layout)
    
    def _create_filter_panel(self) -> QGroupBox:
        """Create the filter panel with search and filter controls"""
        filter_group = QGroupBox("Filters")
        filter_group.setCheckable(True)
        filter_group.setChecked(True)
        filter_layout = QVBoxLayout(filter_group)
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search channels by name, location, sensor ID...")
        self.search_box.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_box)
        filter_layout.addLayout(search_layout)
        
        # Sensor type filter
        sensor_layout = QHBoxLayout()
        sensor_layout.addWidget(QLabel("Sensor Type:"))
        self.sensor_type_checks = {}
        for sensor_type in ["Accelerometer", "Pressure", "Temperature", "Strain Gage"]:
            cb = QCheckBox(sensor_type)
            cb.stateChanged.connect(self._on_filter_changed)
            self.sensor_type_checks[sensor_type] = cb
            sensor_layout.addWidget(cb)
        sensor_layout.addStretch()
        filter_layout.addLayout(sensor_layout)
        
        # Location filter
        location_layout = QHBoxLayout()
        location_layout.addWidget(QLabel("Location:"))
        self.location_filter = QLineEdit()
        self.location_filter.setPlaceholderText("Filter locations (contains, case-insensitive)")
        self.location_filter.textChanged.connect(self._on_filter_changed)
        location_layout.addWidget(self.location_filter, stretch=1)
        
        # Apply/Reset buttons
        apply_btn = QPushButton("Apply Filters")
        apply_btn.clicked.connect(self._apply_filters)
        location_layout.addWidget(apply_btn)
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_filters)
        location_layout.addWidget(reset_btn)
        
        filter_layout.addLayout(location_layout)
        
        # Result count and tree expansion behavior
        options_layout = QHBoxLayout()
        self.result_label = QLabel("Showing all channels")
        self.result_label.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        options_layout.addWidget(self.result_label)
        options_layout.addStretch()

        self.always_expanded_check = QCheckBox("Always Expanded")
        self.always_expanded_check.setChecked(True)
        self.always_expanded_check.setToolTip(
            "Keep channel trees expanded after filtering and view changes."
        )
        self.always_expanded_check.stateChanged.connect(self._on_tree_expansion_changed)
        options_layout.addWidget(self.always_expanded_check)

        filter_layout.addLayout(options_layout)
        
        return filter_group
    
    def _create_view_mode_panel(self) -> QHBoxLayout:
        """Create the view mode selection panel"""
        view_layout = QHBoxLayout()
        view_layout.addWidget(QLabel("View Mode:"))
        
        self.view_mode_group = {}
        for mode in ViewMode:
            rb = QRadioButton(mode.value)
            rb.toggled.connect(lambda checked, m=mode: self._on_view_mode_changed(m) if checked else None)
            self.view_mode_group[mode] = rb
            view_layout.addWidget(rb)
            
        self.view_mode_group[ViewMode.BY_FLIGHT].setChecked(True)
        view_layout.addStretch()
        
        # Column customization button
        customize_btn = QPushButton("Customize Columns...")
        customize_btn.clicked.connect(self._customize_columns)
        view_layout.addWidget(customize_btn)
        
        return view_layout
    
    def _create_button_panel(self) -> QHBoxLayout:
        """Create the bottom button panel"""
        button_layout = QHBoxLayout()
        
        # Selection management
        self.recent_combo = QComboBox()
        self.recent_combo.addItem("Recent Selections...")
        self.recent_combo.currentTextChanged.connect(self._on_recent_selection)
        button_layout.addWidget(self.recent_combo)
        
        save_btn = QPushButton("Save Selection...")
        save_btn.clicked.connect(self._save_selection)
        button_layout.addWidget(save_btn)
        
        button_layout.addStretch()
        
        # Select all/none
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all)
        button_layout.addWidget(deselect_all_btn)
        
        # Load button
        self.load_button = QPushButton("Load Selected")
        self.load_button.setObjectName("loadButton")
        self.load_button.clicked.connect(self._on_load_clicked)
        self.load_button.setEnabled(False)
        button_layout.addWidget(self.load_button)
        
        return button_layout

    def _apply_tree_header_styling(self):
        """Apply deterministic header styling regardless of parent stylesheet."""
        if not hasattr(self, "tree"):
            return
        header = self.tree.header()
        if header is None:
            return
        header.setObjectName("channelTreeHeader")
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #1a1f2e;
                color: #60a5fa;
                font-weight: bold;
                border: 1px solid #4a5568;
                padding: 4px;
            }
        """)

    
    def _load_all_channels(self):
        """Load all channels from the HDF5 file into memory for filtering"""
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import Qt
        
        self.all_channels = []
        
        # Count total channels for progress tracking
        total_channels = sum(
            len(self.loader.get_channel_keys(fk)) 
            for fk in self.loader.get_flight_keys()
        )
        
        # Create progress dialog (only shows if loading takes > 500ms)
        progress = QProgressDialog(
            "Loading channel information...", 
            "Cancel", 
            0, 
            total_channels, 
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(500)  # Only show if takes > 0.5s
        progress.setWindowTitle("Enhanced Flight Navigator")
        
        channel_count = 0
        cancelled = False
        
        for flight_key in self.loader.get_flight_keys():
            if cancelled:
                break
                
            flight_info = self.loader.get_flight_info(flight_key)
            for channel_key in self.loader.get_channel_keys(flight_key):
                # Update progress
                progress.setValue(channel_count)
                if progress.wasCanceled():
                    cancelled = True
                    break
                
                channel_info = self.loader.get_channel_info(flight_key, channel_key)
                
                # Get time range (OPTIMIZED: reads only first and last values)
                time_range = self.loader.get_time_range(flight_key, channel_key)
                
                # Infer sensor type from channel units and name
                sensor_type = self._infer_sensor_type(channel_key, channel_info)
                
                # Store channel data
                self.all_channels.append({
                    'flight_key': flight_key,
                    'channel_key': channel_key,
                    'channel_info': channel_info,
                    'flight_info': flight_info,
                    'time_range': time_range,
                    'sensor_type': sensor_type
                })
                
                channel_count += 1
        
        progress.close()
        
        # If cancelled, close dialog and return
        if cancelled:
            self.reject()
            return
        
        self.filtered_channels = self.all_channels.copy()

    def _safe_text(self, value, fallback: str = "") -> str:
        """Convert optional metadata to a safe display/filter string."""
        if value is None:
            return fallback
        text = str(value).strip()
        if not text:
            return fallback
        return text

    def _normalize_units(self, units: str) -> str:
        """Normalize units to improve robust matching across source variants."""
        normalized = self._safe_text(units).lower()
        replacements = (
            ("\u00b2", "2"),
            ("\u00b0", "deg"),
            ("\u00b5", "u"),
            ("\u03bc", "u"),
            ("\u03b5", "e"),
            ("^2", "2"),
            ("\u00c2\u00b2", "2"),
            ("\u00c2\u00b0", "deg"),
            ("\u00c2\u00b5", "u"),
            ("\u00ce\u00bc", "u"),
            ("-", " "),
            ("_", " "),
        )
        for old, new in replacements:
            normalized = normalized.replace(old, new)
        return re.sub(r"\s+", " ", normalized).strip()
    
    def _infer_sensor_type(self, channel_key: str, channel_info) -> str:
        """Infer sensor type from channel units (primary) and name (fallback)"""
        # Get units from channel_info
        units = self._normalize_units(getattr(channel_info, 'units', ''))
        units_compact = units.replace(" ", "")
        
        # Map units to sensor types
        if units:
            acceleration_units = {
                "g", "gs", "grms", "gpk", "gpeak",
                "m/s2", "m/sec2", "m/s/s",
                "in/s2", "in/sec2",
                "ft/s2", "ft/sec2",
                "mm/s2", "cm/s2",
            }
            # Accelerometer: g, g-rms style, m/s2, in/s2, ft/s2, etc.
            if units_compact in acceleration_units or (
                units_compact.startswith("g") and "rms" in units_compact
            ):
                return "Accelerometer"
            
            pressure_units = {
                "pa", "kpa", "mpa", "bar", "mbar", "torr", "atm", "mmhg", "inhg",
            }
            # Pressure: PSI-family variants and standard pressure units.
            if "psi" in units_compact or units_compact in pressure_units:
                return "Pressure"
            
            # Temperature: C/F/K with degree and alias variants.
            if units_compact in {"c", "f", "k", "degc", "degf", "celsius", "fahrenheit", "kelvin"}:
                return "Temperature"
            
            # Strain: microstrain variants.
            if units_compact in {"microstrain", "strain", "ue", "ustrain"}:
                return "Strain Gage"
        
        # Fallback to name-based inference if units don't match
        name_lower = channel_key.lower()
        if 'accel' in name_lower or 'acc_' in name_lower:
            return "Accelerometer"
        elif 'strain' in name_lower or 'sg_' in name_lower:
            return "Strain Gage"
        elif 'press' in name_lower or 'pres_' in name_lower:
            return "Pressure"
        elif 'temp' in name_lower:
            return "Temperature"
        else:
            return "Unknown"
    
    def _update_tree_columns(self):
        """Update tree widget columns based on configuration"""
        visible_columns = [col for col in self.columns if col.visible]
        self.tree.setColumnCount(len(visible_columns))
        self.tree.setHeaderLabels([col.title for col in visible_columns])
        
        for i, col in enumerate(visible_columns):
            self.tree.setColumnWidth(i, col.width)
    
    def _populate_tree(self):
        """Populate tree widget based on current view mode and filters"""
        self.tree.clear()
        self.tree.itemChanged.disconnect(self._on_item_changed)
        
        if self.current_view_mode == ViewMode.BY_FLIGHT:
            self._populate_by_flight()
        elif self.current_view_mode == ViewMode.BY_LOCATION:
            self._populate_by_location()
        elif self.current_view_mode == ViewMode.BY_SENSOR_TYPE:
            self._populate_by_sensor_type()
        
        self.tree.itemChanged.connect(self._on_item_changed)
        self._update_result_label()
        if self.always_expanded_check.isChecked():
            self.tree.expandAll()
        else:
            self.tree.collapseAll()

    def _on_tree_expansion_changed(self, _state: int):
        """Handle Always Expanded toggle for tree item expansion."""
        if not hasattr(self, "tree"):
            return
        if self.always_expanded_check.isChecked():
            self.tree.expandAll()
        else:
            self.tree.collapseAll()

    def showEvent(self, event):
        """Reassert header styling after Qt style/theme recalculation."""
        super().showEvent(event)
        self._apply_tree_header_styling()
    
    def _populate_by_flight(self):
        """Populate tree in 'By Flight' view mode"""
        flights = {}
        for channel_data in self.filtered_channels:
            flight_key = channel_data['flight_key']
            if flight_key not in flights:
                flights[flight_key] = []
            flights[flight_key].append(channel_data)
        
        for flight_key in sorted(flights.keys()):
            flight_info = flights[flight_key][0]['flight_info']
            flight_item = QTreeWidgetItem(self.tree)
            flight_item.setText(0, f"{flight_key} ({len(flights[flight_key])} channels)")
            flight_item.setFlags(flight_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            flight_item.setCheckState(0, Qt.CheckState.Unchecked)
            flight_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'flight', 'key': flight_key})
            
            for channel_data in sorted(flights[flight_key], key=lambda x: x['channel_key']):
                channel_item = self._create_channel_item(channel_data)
                flight_item.addChild(channel_item)
    
    def _populate_by_location(self):
        """Populate tree in 'By Location' view mode"""
        locations = {}
        for channel_data in self.filtered_channels:
            location = self._safe_text(getattr(channel_data['channel_info'], 'location', ''), 'Unknown')
            if location not in locations:
                locations[location] = []
            locations[location].append(channel_data)
        
        for location in sorted(locations.keys()):
            location_item = QTreeWidgetItem(self.tree)
            location_item.setText(0, f"{location} ({len(locations[location])} channels)")
            location_item.setFlags(location_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            location_item.setCheckState(0, Qt.CheckState.Unchecked)
            location_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'location', 'key': location})
            
            for channel_data in sorted(locations[location], key=lambda x: x['channel_key']):
                channel_item = self._create_channel_item(channel_data)
                location_item.addChild(channel_item)
    
    def _populate_by_sensor_type(self):
        """Populate tree in 'By Sensor Type' view mode"""
        sensor_types = {}
        for channel_data in self.filtered_channels:
            sensor_type = channel_data['sensor_type']
            if sensor_type not in sensor_types:
                sensor_types[sensor_type] = []
            sensor_types[sensor_type].append(channel_data)
        
        for sensor_type in sorted(sensor_types.keys()):
            type_item = QTreeWidgetItem(self.tree)
            type_item.setText(0, f"{sensor_type} ({len(sensor_types[sensor_type])} channels)")
            type_item.setFlags(type_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            type_item.setCheckState(0, Qt.CheckState.Unchecked)
            type_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'sensor_type', 'key': sensor_type})
            
            for channel_data in sorted(sensor_types[sensor_type], key=lambda x: x['channel_key']):
                channel_item = self._create_channel_item(channel_data)
                type_item.addChild(channel_item)
    
    def _create_channel_item(self, channel_data: dict) -> QTreeWidgetItem:
        """Create a tree widget item for a channel"""
        channel_item = QTreeWidgetItem()
        channel_item.setFlags(channel_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        channel_item.setCheckState(0, Qt.CheckState.Unchecked)
        
        # Store data
        channel_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'channel',
            'flight_key': channel_data['flight_key'],
            'channel_key': channel_data['channel_key'],
            'channel_info': channel_data['channel_info']
        })
        
        # Set column values based on visible columns
        visible_columns = [col for col in self.columns if col.visible]
        channel_info = channel_data['channel_info']
        
        for i, col in enumerate(visible_columns):
            if col.name == "name":
                channel_item.setText(i, channel_data['channel_key'])
            elif col.name == "units":
                channel_item.setText(i, self._safe_text(getattr(channel_info, 'units', None), 'N/A'))
            elif col.name == "sample_rate":
                sr = getattr(channel_info, 'sample_rate', None)
                if isinstance(sr, (int, float)) and sr > 0:
                    channel_item.setText(i, f"{sr} Hz")
                else:
                    channel_item.setText(i, "N/A")
            elif col.name == "location":
                channel_item.setText(i, self._safe_text(getattr(channel_info, 'location', None), 'N/A'))
            elif col.name == "time_range":
                channel_item.setText(i, self._safe_text(channel_data.get('time_range', None), 'N/A'))
            elif col.name == "sensor_id":
                channel_item.setText(i, self._safe_text(getattr(channel_info, 'sensor_id', None), 'N/A'))
            elif col.name == "description":
                channel_item.setText(i, self._safe_text(getattr(channel_info, 'description', None), 'N/A'))
            elif col.name == "range":
                range_min = getattr(channel_info, 'range_min', None)
                range_max = getattr(channel_info, 'range_max', None)
                if range_min is not None and range_max is not None:
                    channel_item.setText(i, f"{range_min} to {range_max}")
                else:
                    channel_item.setText(i, 'N/A')
            elif col.name == "flight":
                channel_item.setText(i, channel_data['flight_key'])
        
        return channel_item

    
    def _on_search_changed(self, text: str):
        """Handle search text changes with debounce"""
        self.search_text = text
        self.search_timer.start(300)  # 300ms debounce
    
    def _on_filter_changed(self):
        """Handle filter changes"""
        # Update sensor type filters
        self.filter_sensor_types = {
            sensor_type for sensor_type, cb in self.sensor_type_checks.items()
            if cb.isChecked()
        }
        
        # Update location filter
        self.filter_location = self._safe_text(self.location_filter.text())
        
        # Apply filters with debounce
        self.search_timer.start(300)
    
    def _apply_filters(self):
        """Apply current search and filter criteria"""
        self.filtered_channels = []
        
        for channel_data in self.all_channels:
            # Check sensor type filter
            if self.filter_sensor_types and channel_data['sensor_type'] not in self.filter_sensor_types:
                continue
            
            # Check location filter
            if self.filter_location:
                channel_location = self._safe_text(
                    getattr(channel_data['channel_info'], 'location', '')
                ).lower()
                if self.filter_location.lower() not in channel_location:
                    continue
            
            # Check search text
            if self.search_text:
                search_lower = self.search_text.lower()
                channel_key_lower = self._safe_text(channel_data.get('channel_key', '')).lower()
                location_lower = self._safe_text(
                    getattr(channel_data['channel_info'], 'location', '')
                ).lower()
                sensor_id_lower = self._safe_text(
                    getattr(channel_data['channel_info'], 'sensor_id', '')
                ).lower()
                description_lower = self._safe_text(
                    getattr(channel_data['channel_info'], 'description', '')
                ).lower()
                
                if not (search_lower in channel_key_lower or
                        search_lower in location_lower or
                        search_lower in sensor_id_lower or
                        search_lower in description_lower):
                    continue
            
            self.filtered_channels.append(channel_data)
        
        # Repopulate tree
        self._populate_tree()
    
    def _reset_filters(self):
        """Reset all filters to default state"""
        self.search_box.clear()
        for cb in self.sensor_type_checks.values():
            cb.setChecked(False)
        self.location_filter.clear()
        self.filter_sensor_types = set()
        self.filter_location = ""
        self.search_text = ""
        self._apply_filters()
    
    def _update_result_label(self):
        """Update the result count label"""
        total = len(self.all_channels)
        filtered = len(self.filtered_channels)
        if filtered == total:
            self.result_label.setText(f"Showing all {total} channels")
        else:
            self.result_label.setText(f"Showing {filtered} of {total} channels")
    
    def _on_view_mode_changed(self, mode: ViewMode):
        """Handle view mode change"""
        if mode != self.current_view_mode:
            self.current_view_mode = mode
            self._populate_tree()
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item check state changes"""
        if column == 0:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data['type'] == 'channel':
                self._update_selection()
    
    def _update_selection(self):
        """Update the selected items list"""
        self.selected_items = []
        
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if item.checkState(0) == Qt.CheckState.Checked:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data['type'] == 'channel':
                    self.selected_items.append((
                        data['flight_key'],
                        data['channel_key'],
                        data['channel_info']
                    ))
            iterator += 1
        
        # Update UI
        count = len(self.selected_items)
        self.summary_label.setText(f"{count} channel{'s' if count != 1 else ''} selected")
        self.load_button.setEnabled(count > 0)
    
    def _select_all(self):
        """Select all visible channels"""
        self.tree.itemChanged.disconnect(self._on_item_changed)
        
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data['type'] == 'channel':
                item.setCheckState(0, Qt.CheckState.Checked)
            iterator += 1
        
        self.tree.itemChanged.connect(self._on_item_changed)
        self._update_selection()
    
    def _deselect_all(self):
        """Deselect all channels"""
        self.tree.itemChanged.disconnect(self._on_item_changed)
        
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            item.setCheckState(0, Qt.CheckState.Unchecked)
            iterator += 1
        
        self.tree.itemChanged.connect(self._on_item_changed)
        self._update_selection()
    
    def _customize_columns(self):
        """Open column customization dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Customize Columns")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select columns to display:"))
        
        checkboxes = {}
        for col in self.columns:
            if col.name == "name":  # Name column always visible
                continue
            cb = QCheckBox(col.title)
            cb.setChecked(col.visible)
            checkboxes[col.name] = cb
            layout.addWidget(cb)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update column visibility
            for col in self.columns:
                if col.name in checkboxes:
                    col.visible = checkboxes[col.name].isChecked()
            
            # Refresh tree
            self._update_tree_columns()
            self._populate_tree()
    
    def _save_selection(self):
        """Save current selection"""
        if not self.selected_items:
            show_warning(self, "No Selection", "Please select channels before saving.")
            return
        
        name, ok = QInputDialog.getText(
            self, "Save Selection",
            "Enter a name for this selection:"
        )
        
        if ok and name:
            selection_data = {
                'items': [(fk, ck) for fk, ck, _ in self.selected_items],
                'view_mode': self.current_view_mode.value
            }
            self.selection_manager.save_selection(name, selection_data)
            show_information(self, "Saved", f"Selection '{name}' saved successfully!")
            self._update_recent_combo()
    
    def _on_recent_selection(self, name: str):
        """Load a recent selection"""
        if name == "Recent Selections...":
            return
        
        selection_data = self.selection_manager.load_selection(name)
        if selection_data:
            self._load_selection_data(selection_data)
    
    def _load_selection_data(self, selection_data: dict):
        """Load selection data and update UI"""
        self._deselect_all()
        
        items_to_select = set(selection_data.get('items', []))
        
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data['type'] == 'channel':
                if (data['flight_key'], data['channel_key']) in items_to_select:
                    item.setCheckState(0, Qt.CheckState.Checked)
            iterator += 1
        
        self._update_selection()
    
    def _update_recent_combo(self):
        """Update recent selections combobox"""
        self.recent_combo.clear()
        self.recent_combo.addItem("Recent Selections...")
        
        recent = self.selection_manager.get_recent_selections()
        for selection in recent:
            self.recent_combo.addItem(selection['name'])
    
    def _on_load_clicked(self):
        """Handle Load Selected button click"""
        if self.selected_items:
            if self.max_selected_channels is not None and len(self.selected_items) > self.max_selected_channels:
                message = self.selection_limit_message or (
                    f"Please select no more than {self.max_selected_channels} channel"
                    f"{'' if self.max_selected_channels == 1 else 's'}."
                )
                show_warning(self, "Selection Limit", message)
                return

            # Save to recent
            selection_data = {
                'items': [(fk, ck) for fk, ck, _ in self.selected_items],
                'view_mode': self.current_view_mode.value
            }
            self.selection_manager.add_recent_selection(
                f"Selection of {len(self.selected_items)} channels",
                selection_data
            )
            self._update_recent_combo()
            
            # Emit signal
            self.data_selected.emit(self.selected_items)
            self.accept()

    def get_selected_channels(self):
        """
        Get the list of selected channels.
        
        Returns:
        --------
        list of tuple
            List of (flight_key, channel_key) tuples for selected channels
        """
        return [(flight_key, channel_key) for flight_key, channel_key, _ in self.selected_items]


# Backward-compatible alias during migration to canonical FlightNavigator name.
EnhancedFlightNavigator = FlightNavigator
