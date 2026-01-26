"""
Flight & Channel Navigator GUI

This module provides a GUI for browsing and selecting flights and channels from HDF5 files.
Users can select multiple flights, view available channels, and load selected data into the
PSD analysis tool.

Author: SpectralEdge Development Team
Date: 2025-01-21
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTreeWidget, QTreeWidgetItem, QGroupBox,
                             QCheckBox, QScrollArea, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader, FlightInfo, ChannelInfo
from spectral_edge.utils.message_box import show_warning
from typing import List, Dict, Tuple


class FlightNavigator(QDialog):
    """
    Dialog for navigating and selecting flights and channels from HDF5 files.
    
    Signals:
    --------
    data_selected : signal
        Emitted when user clicks "Load Selected" with list of (flight_key, channel_key) tuples
    """
    
    # Signal emitted when data is selected
    data_selected = pyqtSignal(object)  # Emits list of (flight_key, channel_key, channel_info) tuples
    
    def __init__(self, loader: HDF5FlightDataLoader, parent=None):
        """
        Initialize Flight Navigator dialog.
        
        Parameters:
        -----------
        loader : HDF5FlightDataLoader
            Initialized HDF5 data loader
        parent : QWidget, optional
            Parent widget
        """
        super().__init__(parent)
        self.loader = loader
        self.selected_items = []  # List of (flight_key, channel_key, channel_info) tuples
        
        self.setWindowTitle("Flight & Channel Navigator")
        self.setModal(False)  # Non-modal dialog
        self.resize(800, 600)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1f2e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 11pt;
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
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 11pt;
                border-radius: 4px;
                min-width: 100px;
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
            QCheckBox {
                color: #e0e0e0;
                font-size: 10pt;
                spacing: 8px;
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
            QScrollArea {
                border: 1px solid #4a5568;
                background-color: #2d3748;
            }
        """)
        
        self._create_ui()
        self._populate_tree()
    
    def _create_ui(self):
        """Create the user interface."""
        layout = QVBoxLayout(self)
        
        # File info label
        file_info = QLabel(f"File: {self.loader.file_path}")
        file_info.setStyleSheet("font-size: 10pt; color: #9ca3af;")
        layout.addWidget(file_info)
        
        # Tree widget for flights and channels
        tree_group = QGroupBox("Flights & Channels")
        tree_layout = QVBoxLayout()
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Name", "Details"])
        self.tree_widget.setColumnWidth(0, 300)
        self.tree_widget.itemChanged.connect(self._on_item_changed)
        tree_layout.addWidget(self.tree_widget)
        
        tree_group.setLayout(tree_layout)
        layout.addWidget(tree_group)
        
        # Selection info
        self.selection_label = QLabel("Selected: 0 channels")
        self.selection_label.setStyleSheet("font-size: 10pt; color: #9ca3af;")
        layout.addWidget(self.selection_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Select All button
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(self.select_all_btn)
        
        # Deselect All button
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        button_layout.addWidget(self.deselect_all_btn)
        
        button_layout.addStretch()
        
        # Load Selected button
        self.load_btn = QPushButton("Load Selected")
        self.load_btn.clicked.connect(self._load_selected)
        self.load_btn.setEnabled(False)
        button_layout.addWidget(self.load_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _populate_tree(self):
        """Populate tree widget with flights and channels."""
        # Temporarily disconnect signal to avoid triggering during population
        self.tree_widget.itemChanged.disconnect(self._on_item_changed)
        
        # Get all flights
        flights = self.loader.get_flights()
        
        for flight in flights:
            # Create flight item
            flight_item = QTreeWidgetItem(self.tree_widget)
            flight_item.setText(0, flight.flight_id)
            flight_item.setText(1, f"{flight.date}, {flight.duration:.1f}s")
            flight_item.setFlags(flight_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            flight_item.setCheckState(0, Qt.CheckState.Unchecked)
            
            # Store flight key in item data
            flight_item.setData(0, Qt.ItemDataRole.UserRole, ('flight', flight.flight_key))
            
            # Make flight item bold
            font = flight_item.font(0)
            font.setBold(True)
            flight_item.setFont(0, font)
            
            # Get channels for this flight
            channels = self.loader.get_channels(flight.flight_key)
            
            for channel in channels:
                # Create channel item
                channel_item = QTreeWidgetItem(flight_item)
                channel_item.setText(0, channel.channel_key)
                channel_item.setText(1, f"{channel.sample_rate:.0f} Hz, {channel.units}")
                channel_item.setFlags(channel_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                channel_item.setCheckState(0, Qt.CheckState.Unchecked)
                
                # Store channel info in item data
                channel_item.setData(0, Qt.ItemDataRole.UserRole, 
                                    ('channel', flight.flight_key, channel.channel_key, channel))
        
        # Expand all flight items
        self.tree_widget.expandAll()
        
        # Reconnect signal
        self.tree_widget.itemChanged.connect(self._on_item_changed)
    
    def _on_item_changed(self, item, column):
        """Handle item check state changes."""
        # Temporarily disconnect to avoid recursive calls
        self.tree_widget.itemChanged.disconnect(self._on_item_changed)
        
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if item_data[0] == 'flight':
            # Flight item changed - update all child channels
            check_state = item.checkState(0)
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, check_state)
        
        elif item_data[0] == 'channel':
            # Channel item changed - update parent flight if needed
            parent = item.parent()
            if parent:
                # Check if all children are checked
                all_checked = True
                any_checked = False
                for i in range(parent.childCount()):
                    child_state = parent.child(i).checkState(0)
                    if child_state == Qt.CheckState.Unchecked:
                        all_checked = False
                    if child_state == Qt.CheckState.Checked:
                        any_checked = True
                
                # Update parent state
                if all_checked:
                    parent.setCheckState(0, Qt.CheckState.Checked)
                elif any_checked:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                else:
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
        
        # Update selection list and UI
        self._update_selection()
        
        # Reconnect signal
        self.tree_widget.itemChanged.connect(self._on_item_changed)
    
    def _update_selection(self):
        """Update the list of selected channels."""
        self.selected_items = []
        
        # Iterate through all items
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            flight_item = root.child(i)
            
            for j in range(flight_item.childCount()):
                channel_item = flight_item.child(j)
                
                if channel_item.checkState(0) == Qt.CheckState.Checked:
                    item_data = channel_item.data(0, Qt.ItemDataRole.UserRole)
                    # item_data = ('channel', flight_key, channel_key, channel_info)
                    self.selected_items.append((item_data[1], item_data[2], item_data[3]))
        
        # Update label
        count = len(self.selected_items)
        self.selection_label.setText(f"Selected: {count} channel{'s' if count != 1 else ''}")
        
        # Enable/disable load button
        self.load_btn.setEnabled(count > 0)
    
    def _select_all(self):
        """Select all channels."""
        self.tree_widget.itemChanged.disconnect(self._on_item_changed)
        
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            flight_item = root.child(i)
            flight_item.setCheckState(0, Qt.CheckState.Checked)
            
            for j in range(flight_item.childCount()):
                channel_item = flight_item.child(j)
                channel_item.setCheckState(0, Qt.CheckState.Checked)
        
        self.tree_widget.itemChanged.connect(self._on_item_changed)
        self._update_selection()
    
    def _deselect_all(self):
        """Deselect all channels."""
        self.tree_widget.itemChanged.disconnect(self._on_item_changed)
        
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            flight_item = root.child(i)
            flight_item.setCheckState(0, Qt.CheckState.Unchecked)
            
            for j in range(flight_item.childCount()):
                channel_item = flight_item.child(j)
                channel_item.setCheckState(0, Qt.CheckState.Unchecked)
        
        self.tree_widget.itemChanged.connect(self._on_item_changed)
        self._update_selection()
    
    def _load_selected(self):
        """Emit signal with selected channels."""
        if not self.selected_items:
            show_warning(self, "No Selection", "Please select at least one channel to load.")
            return
        
        # Emit signal with selected items
        self.data_selected.emit(self.selected_items)
        
        # Close dialog
        self.accept()
    
    def get_selected_channels(self) -> List[Tuple[str, str, ChannelInfo]]:
        """
        Get list of selected channels.
        
        Returns:
        --------
        list of tuples
            List of (flight_key, channel_key, channel_info) tuples
        """
        return self.selected_items
