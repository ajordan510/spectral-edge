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
from typing import List, Dict, Tuple, Set
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
    
    def __init__(self, loader: HDF5FlightDataLoader, parent=None):
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
        
        # Data storage
        self.selected_items = []  # List of (flight_key, channel_key, channel_info)
        self.all_channels = []  # All channels for filtering
        self.filtered_channels = []  # Channels after filtering
        
        # View mode
        self.current_view_mode = ViewMode.BY_FLIGHT
        
        # Column configuration (default visible: Name, Units, Sample Rate, Location)
        self.columns = [
            ColumnConfig("name", "Channel Name", True, 200),
            ColumnConfig("units", "Units", True, 80),
            ColumnConfig("sample_rate", "Sample Rate", True, 100),
            ColumnConfig("location", "Location", True, 150),
            ColumnConfig("time_range", "Time Range", False, 120),
            ColumnConfig("sensor_id", "Sensor ID", False, 100),
            ColumnConfig("description", "Description", False, 200),
            ColumnConfig("range", "Range", False, 100),
            ColumnConfig("flight", "Flight", False, 100),
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
            QTreeWidget {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                font-size: 10pt;
            }
            QTreeWidget::item:hover {
                background-color: #4a5568;
            }
            QTreeWidget::item:selected {
                background-color: #3b82f6;
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
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.itemChanged.connect(self._on_item_changed)
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
        for sensor_type in ["Accelerometer", "Microphone", "Strain Gage", "Pressure", "Temperature"]:
            cb = QCheckBox(sensor_type)
            cb.stateChanged.connect(self._on_filter_changed)
            self.sensor_type_checks[sensor_type] = cb
            sensor_layout.addWidget(cb)
        sensor_layout.addStretch()
        filter_layout.addLayout(sensor_layout)
        
        # Location filter
        location_layout = QHBoxLayout()
        location_layout.addWidget(QLabel("Location:"))
        self.location_combo = QComboBox()
        self.location_combo.addItem("All Locations")
        self.location_combo.currentTextChanged.connect(self._on_filter_changed)
        location_layout.addWidget(self.location_combo, stretch=1)
        
        # Apply/Reset buttons
        apply_btn = QPushButton("Apply Filters")
        apply_btn.clicked.connect(self._apply_filters)
        location_layout.addWidget(apply_btn)
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_filters)
        location_layout.addWidget(reset_btn)
        
        filter_layout.addLayout(location_layout)
        
        # Result count and options
        options_layout = QHBoxLayout()
        self.result_label = QLabel("Showing all channels")
        self.result_label.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        options_layout.addWidget(self.result_label)
        
        options_layout.addStretch()
        
        # Keep tree expanded checkbox
        self.keep_expanded_check = QCheckBox("Keep Tree Expanded")
        self.keep_expanded_check.setChecked(True)  # Default to expanded
        self.keep_expanded_check.setToolTip("Automatically expand all tree items after filtering/searching")
        options_layout.addWidget(self.keep_expanded_check)
        
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

    
    def _load_all_channels(self):
        """
        Load all channels from the HDF5 file into memory for filtering.
        
        This method iterates through all flights and channels, extracting
        metadata for display in the navigator. Time data is loaded to
        determine time ranges for each channel.
        
        Raises:
        -------
        Exception
            If there's an error loading channel data, it's caught and
            the channel is skipped with a warning.
        """
        self.all_channels = []
        locations = set()
        errors = []
        
        try:
            flight_keys = self.loader.get_flight_keys()
            print(f"Loading {len(flight_keys)} flights...")
            
            for flight_key in flight_keys:
                try:
                    flight_info = self.loader.get_flight_info(flight_key)
                    channel_keys = self.loader.get_channel_keys(flight_key)
                    print(f"  Flight {flight_key}: {len(channel_keys)} channels")
                    
                    for channel_key in channel_keys:
                        try:
                            channel_info = self.loader.get_channel_info(flight_key, channel_key)
                            
                            # Time range from metadata (avoid loading actual data for speed)
                            # Use start_time and duration from channel/flight metadata if available
                            start_time = getattr(channel_info, 'start_time', 0.0)
                            duration = getattr(flight_info, 'duration', None) if flight_info else None
                            if duration is not None:
                                time_range = f"{start_time:.1f}s - {start_time + duration:.1f}s"
                            else:
                                time_range = "N/A"
                            
                            # Infer sensor type from channel name
                            sensor_type = self._infer_sensor_type(channel_key)
                            
                            # Store channel data
                            self.all_channels.append({
                                'flight_key': flight_key,
                                'channel_key': channel_key,
                                'channel_info': channel_info,
                                'flight_info': flight_info,
                                'time_range': time_range,
                                'sensor_type': sensor_type
                            })
                            
                            # Collect unique locations
                            if hasattr(channel_info, 'location') and channel_info.location:
                                locations.add(channel_info.location)
                                
                        except Exception as e:
                            errors.append(f"{flight_key}/{channel_key}: {e}")
                            continue
                            
                except Exception as e:
                    errors.append(f"Flight {flight_key}: {e}")
                    continue
            
            print(f"Loaded {len(self.all_channels)} channels total")
            
            if errors:
                print(f"Warnings during load: {len(errors)} errors")
                for err in errors[:5]:  # Show first 5 errors
                    print(f"  - {err}")
                    
        except Exception as e:
            print(f"Critical error loading channels: {e}")
            show_warning(self, "Load Warning", f"Error loading some channels: {e}")
        
        # Populate location filter
        for location in sorted(locations):
            self.location_combo.addItem(location)
        
        self.filtered_channels = self.all_channels.copy()
    
    def _infer_sensor_type(self, channel_name: str) -> str:
        """Infer sensor type from channel name"""
        name_lower = channel_name.lower()
        if 'accel' in name_lower or 'acc_' in name_lower:
            return "Accelerometer"
        elif 'mic' in name_lower or 'microphone' in name_lower:
            return "Microphone"
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
        
        # Safely disconnect signal (may not be connected on first call)
        try:
            self.tree.itemChanged.disconnect(self._on_item_changed)
        except (TypeError, RuntimeError):
            pass  # Signal was not connected
        
        if self.current_view_mode == ViewMode.BY_FLIGHT:
            self._populate_by_flight()
        elif self.current_view_mode == ViewMode.BY_LOCATION:
            self._populate_by_location()
        elif self.current_view_mode == ViewMode.BY_SENSOR_TYPE:
            self._populate_by_sensor_type()
        
        self.tree.itemChanged.connect(self._on_item_changed)
        self._update_result_label()
        
        # Expand all items if option is enabled
        if self.keep_expanded_check.isChecked():
            self.tree.expandAll()
    
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
            location = getattr(channel_data['channel_info'], 'location', 'Unknown')
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
                channel_item.setText(i, getattr(channel_info, 'units', 'N/A'))
            elif col.name == "sample_rate":
                sr = getattr(channel_info, 'sample_rate', None)
                channel_item.setText(i, f"{sr} Hz" if sr else 'N/A')
            elif col.name == "location":
                channel_item.setText(i, getattr(channel_info, 'location', 'N/A'))
            elif col.name == "time_range":
                channel_item.setText(i, channel_data['time_range'])
            elif col.name == "sensor_id":
                channel_item.setText(i, getattr(channel_info, 'sensor_id', 'N/A'))
            elif col.name == "description":
                channel_item.setText(i, getattr(channel_info, 'description', 'N/A'))
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
        location_text = self.location_combo.currentText()
        self.filter_location = "" if location_text == "All Locations" else location_text
        
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
                channel_location = getattr(channel_data['channel_info'], 'location', '')
                if channel_location != self.filter_location:
                    continue
            
            # Check search text
            if self.search_text:
                search_lower = self.search_text.lower()
                channel_key_lower = channel_data['channel_key'].lower()
                location_lower = getattr(channel_data['channel_info'], 'location', '').lower()
                sensor_id_lower = getattr(channel_data['channel_info'], 'sensor_id', '').lower()
                description_lower = getattr(channel_data['channel_info'], 'description', '').lower()
                
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
        self.location_combo.setCurrentIndex(0)
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
        try:
            self.tree.itemChanged.disconnect(self._on_item_changed)
        except (TypeError, RuntimeError):
            pass
        
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
        try:
            self.tree.itemChanged.disconnect(self._on_item_changed)
        except (TypeError, RuntimeError):
            pass
        
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
        
        # Find the selection in recent list by name
        recent = self.selection_manager.get_recent_selections()
        for selection in recent:
            if selection.get('name') == name:
                selection_data = selection.get('data', {})
                if selection_data:
                    self._load_selection_data(selection_data)
                break
    
    def _load_selection_data(self, selection_data: dict):
        """Load selection data and update UI"""
        self._deselect_all()
        
        # Convert items list to set of tuples for fast lookup
        items_list = selection_data.get('items', [])
        items_to_select = set(tuple(item) if isinstance(item, list) else item for item in items_list)
        
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
