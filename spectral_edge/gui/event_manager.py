"""
Event Manager GUI window for SpectralEdge.

This module provides a window for managing time-based events within signal data,
allowing users to define, edit, and save event definitions for segmented PSD analysis.

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QDoubleSpinBox, QFileDialog, QHeaderView, QComboBox
)
from spectral_edge.utils.message_box import show_information, show_warning, show_critical
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import json
from pathlib import Path


class Event:
    """
    Represents a time-based event within signal data.
    
    An event is defined by a name, start time, and end time.
    """
    
    def __init__(self, name, start_time, end_time):
        """
        Initialize an event.
        
        Args:
            name: Name/label for the event
            start_time: Start time in seconds
            end_time: End time in seconds
        """
        self.name = name
        self.start_time = start_time
        self.end_time = end_time
    
    @property
    def duration(self):
        """Calculate event duration in seconds."""
        return self.end_time - self.start_time
    
    def to_dict(self):
        """Convert event to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'start': self.start_time,
            'end': self.end_time
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create event from dictionary."""
        return cls(data['name'], data['start'], data['end'])


class EventManagerWindow(QMainWindow):
    """
    Window for managing time-based events for PSD analysis.
    
    This window allows users to:
    - Define events with start and end times
    - Edit event properties
    - Add and remove events
    - Save and load event definitions
    - Apply event templates
    - Enable interactive selection mode
    """
    
    # Signal emitted when events are updated
    events_updated = pyqtSignal(list)  # List of Event objects
    
    # Signal emitted when interactive mode is toggled
    interactive_mode_changed = pyqtSignal(bool)
    
    def __init__(self, max_time=None, min_time=0.0):
        """
        Initialize the Event Manager window.
        
        Args:
            max_time: Maximum time value from the loaded data (for validation)
            min_time: Minimum time value from the loaded data (for validation)
        """
        super().__init__()
        
        self.min_time = float(min_time)
        self.max_time = max_time if max_time else 100.0
        if self.max_time <= self.min_time:
            self.max_time = self.min_time + 1.0
        self.events = []  # List of Event objects
        self.interactive_mode = False
        
        # Window properties
        self.setWindowTitle("SpectralEdge - Event Manager")
        self.setMinimumSize(800, 600)
        
        # Apply styling
        self._apply_styling()
        
        # Create UI
        self._create_ui()
        
        # Add a default "Full" event
        self._add_default_full_event()
    
    def _apply_styling(self):
        """Apply aerospace-inspired styling."""
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
            QTableWidget {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 2px solid #4a5568;
                gridline-color: #4a5568;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #60a5fa;
            }
            QHeaderView::section {
                background-color: #1a1f2e;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                padding: 5px;
                font-weight: bold;
            }
            QLineEdit, QDoubleSpinBox, QComboBox {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 5px;
            }
        """)
    
    def _create_ui(self):
        """Create the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Event Manager")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #60a5fa;")
        layout.addWidget(title)
        
        # Info label
        info_label = QLabel(
            "Define time-based events for segmented PSD analysis. "
            "Events can be added manually or selected interactively from the time history plot."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        layout.addWidget(info_label)
        
        # Event table
        self.table = self._create_event_table()
        layout.addWidget(self.table)
        
        # Button panel
        button_panel = self._create_button_panel()
        layout.addWidget(button_panel)
        
        # Template panel
        template_panel = self._create_template_panel()
        layout.addWidget(template_panel)
        
        # Apply and close buttons
        action_panel = self._create_action_panel()
        layout.addWidget(action_panel)
    
    def _create_event_table(self):
        """Create the event table widget."""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Enabled", "Name", "Start (s)", "End (s)", "Duration (s)"])
        
        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        table.setColumnWidth(0, 80)
        table.setColumnWidth(2, 100)
        table.setColumnWidth(3, 100)
        table.setColumnWidth(4, 100)
        
        # Enable editing
        table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        
        # Connect cell changed signal
        table.cellChanged.connect(self._on_cell_changed)
        
        return table
    
    def _create_button_panel(self):
        """Create button panel for event management."""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        
        # Add event button
        add_button = QPushButton("Add Event")
        add_button.clicked.connect(self._add_event)
        layout.addWidget(add_button)
        
        # Remove event button
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._remove_event)
        layout.addWidget(remove_button)
        
        # Interactive selection toggle
        self.interactive_button = QPushButton("Enable Interactive Selection")
        self.interactive_button.setCheckable(True)
        self.interactive_button.clicked.connect(self._toggle_interactive_mode)
        self.interactive_button.setStyleSheet("""
            QPushButton {
                background-color: #2d3748;
            }
            QPushButton:checked {
                background-color: #2563eb;
                border-color: #3b82f6;
            }
        """)
        layout.addWidget(self.interactive_button)
        
        layout.addStretch()
        
        return panel
    
    def _create_template_panel(self):
        """Create template selection panel."""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        
        layout.addWidget(QLabel("Templates:"))
        
        # Template dropdown
        self.template_combo = QComboBox()
        self.template_combo.addItem("Select Template...")
        self.template_combo.addItem("First 10 seconds")
        self.template_combo.addItem("Last 10 seconds")
        self.template_combo.addItem("First 25%")
        self.template_combo.addItem("Middle 50%")
        self.template_combo.addItem("Last 25%")
        self.template_combo.addItem("Quarters (4 events)")
        self.template_combo.addItem("Thirds (3 events)")
        layout.addWidget(self.template_combo)
        
        # Apply template button
        apply_template_button = QPushButton("Apply Template")
        apply_template_button.clicked.connect(self._apply_template)
        layout.addWidget(apply_template_button)
        
        layout.addStretch()
        
        return panel
    
    def _create_action_panel(self):
        """Create action button panel."""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        
        # Save events button
        save_button = QPushButton("Save Events...")
        save_button.clicked.connect(self._save_events)
        layout.addWidget(save_button)
        
        # Load events button
        load_button = QPushButton("Load Events...")
        load_button.clicked.connect(self._load_events)
        layout.addWidget(load_button)
        
        layout.addStretch()
        
        # Apply button
        apply_button = QPushButton("Apply Events")
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
        """)
        apply_button.clicked.connect(self._apply_events)
        layout.addWidget(apply_button)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        return panel
    
    def _add_default_full_event(self):
        """Add default 'Full' event covering entire time range."""
        full_event = Event("Full", self.min_time, self.max_time)
        self.events.append(full_event)
        self._update_table()
    
    def _add_event(self):
        """Add a new event."""
        # Generate unique name
        event_num = len([e for e in self.events if e.name.startswith("Event")]) + 1
        name = f"Event {event_num}"
        
        total_duration = self.max_time - self.min_time
        default_duration = min(10.0, total_duration * 0.1)
        
        event = Event(name, self.min_time, self.min_time + default_duration)
        self.events.append(event)
        self._update_table()
    
    def _remove_event(self):
        """Remove selected event."""
        current_row = self.table.currentRow()
        if current_row >= 0 and current_row < len(self.events):
            # Allow removing "Full" only if at least one other event exists
            if current_row == 0 and self.events[0].name == "Full" and len(self.events) == 1:
                show_warning(self, "Cannot Remove", "The 'Full' event cannot be removed.")
                return
            
            del self.events[current_row]
            self._update_table()
    
    def _toggle_interactive_mode(self, checked):
        """Toggle interactive selection mode."""
        self.interactive_mode = checked
        
        if checked:
            self.interactive_button.setText("Disable Interactive Selection")
        else:
            self.interactive_button.setText("Enable Interactive Selection")
        
        # Emit signal
        self.interactive_mode_changed.emit(checked)
    
    def _apply_template(self):
        """Apply selected template."""
        template = self.template_combo.currentText()
        
        if template == "Select Template...":
            return
        
        # Clear existing events except "Full"
        self.events = [e for e in self.events if e.name == "Full"]
        
        # Apply template
        if template == "First 10 seconds":
            total_duration = self.max_time - self.min_time
            duration = min(10.0, total_duration)
            self.events.append(Event("First 10s", self.min_time, self.min_time + duration))
        
        elif template == "Last 10 seconds":
            total_duration = self.max_time - self.min_time
            duration = min(10.0, total_duration)
            self.events.append(Event("Last 10s", self.max_time - duration, self.max_time))
        
        elif template == "First 25%":
            end_time = self.min_time + (self.max_time - self.min_time) * 0.25
            self.events.append(Event("First 25%", self.min_time, end_time))
        
        elif template == "Middle 50%":
            span = self.max_time - self.min_time
            start_time = self.min_time + span * 0.25
            end_time = self.min_time + span * 0.75
            self.events.append(Event("Middle 50%", start_time, end_time))
        
        elif template == "Last 25%":
            start_time = self.min_time + (self.max_time - self.min_time) * 0.75
            self.events.append(Event("Last 25%", start_time, self.max_time))
        
        elif template == "Quarters (4 events)":
            quarter = (self.max_time - self.min_time) / 4
            self.events.append(Event("Q1", self.min_time, self.min_time + quarter))
            self.events.append(Event("Q2", self.min_time + quarter, self.min_time + 2 * quarter))
            self.events.append(Event("Q3", self.min_time + 2 * quarter, self.min_time + 3 * quarter))
            self.events.append(Event("Q4", self.min_time + 3 * quarter, self.max_time))
        
        elif template == "Thirds (3 events)":
            third = (self.max_time - self.min_time) / 3
            self.events.append(Event("T1", self.min_time, self.min_time + third))
            self.events.append(Event("T2", self.min_time + third, self.min_time + 2 * third))
            self.events.append(Event("T3", self.min_time + 2 * third, self.max_time))
        
        self._update_table()
        
        # Reset template selection
        self.template_combo.setCurrentIndex(0)
    
    def _update_table(self):
        """Update the table with current events."""
        # Block signals to prevent triggering cellChanged
        self.table.blockSignals(True)
        
        self.table.setRowCount(len(self.events))
        
        for i, event in enumerate(self.events):
            # Enabled checkbox
            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            enabled_item.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(i, 0, enabled_item)
            
            # Name
            name_item = QTableWidgetItem(event.name)
            self.table.setItem(i, 1, name_item)
            
            # Start time
            start_item = QTableWidgetItem(f"{event.start_time:.3f}")
            self.table.setItem(i, 2, start_item)
            
            # End time
            end_item = QTableWidgetItem(f"{event.end_time:.3f}")
            self.table.setItem(i, 3, end_item)
            
            # Duration (read-only)
            duration_item = QTableWidgetItem(f"{event.duration:.3f}")
            duration_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            duration_item.setForeground(QColor("#9ca3af"))
            self.table.setItem(i, 4, duration_item)
        
        # Unblock signals
        self.table.blockSignals(False)
    
    def _on_cell_changed(self, row, column):
        """Handle cell changes in the table."""
        if row >= len(self.events):
            return
        
        event = self.events[row]
        
        try:
            if column == 1:  # Name
                event.name = self.table.item(row, column).text()
            
            elif column == 2:  # Start time
                start_time = float(self.table.item(row, column).text())
                if start_time >= self.min_time:
                    event.start_time = start_time
                else:
                    raise ValueError(f"Start time must be >= {self.min_time:.3f}")
            
            elif column == 3:  # End time
                end_time = float(self.table.item(row, column).text())
                if end_time <= self.max_time:
                    event.end_time = end_time
                else:
                    raise ValueError(f"End time must be <= {self.max_time:.3f}")
            
            # Update duration
            self._update_table()
        
        except ValueError as e:
            show_warning(self, "Invalid Value", str(e))
            self._update_table()  # Reset to previous values

    def _validate_events_for_apply(self):
        """Validate events before applying or saving."""
        errors = []
        min_time = self.min_time
        max_time = self.max_time

        for idx, event in enumerate(self.events, start=1):
            label = event.name or f"Event {idx}"
            if event.start_time < min_time:
                event.start_time = min_time
            if event.end_time > max_time:
                event.end_time = max_time
            if event.start_time >= event.end_time:
                errors.append(f"{label}: Start time must be less than end time")
        return errors
    
    def _save_events(self):
        """Save events to JSON file."""
        errors = self._validate_events_for_apply()
        if errors:
            show_warning(self, "Invalid Events", "\n".join(errors))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Events",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            data = {
                'events': [e.to_dict() for e in self.events]
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            show_information(self, "Success", f"Events saved to {Path(file_path).name}")
        
        except Exception as e:
            show_critical(self, "Error", f"Failed to save events: {e}")
    
    def _load_events(self):
        """Load events from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Events",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            self.events = [Event.from_dict(e) for e in data['events']]
            self._update_table()
            
            show_information(self, "Success", f"Events loaded from {Path(file_path).name}")
        
        except Exception as e:
            show_critical(self, "Error", f"Failed to load events: {e}")
    
    def _apply_events(self):
        """Apply events and emit signal."""
        errors = self._validate_events_for_apply()
        if errors:
            show_warning(self, "Invalid Events", "\n".join(errors))
            return

        # Get enabled events
        enabled_events = []
        for i, event in enumerate(self.events):
            checkbox_item = self.table.item(i, 0)
            if checkbox_item.checkState() == Qt.CheckState.Checked:
                enabled_events.append(event)
        
        if not enabled_events:
            show_warning(self, "No Events", "Please enable at least one event.")
            return
        
        # Emit signal with enabled events
        self.events_updated.emit(enabled_events)
        
        show_information(self, "Success", f"Applied {len(enabled_events)} event(s) for PSD calculation.")
    
    def add_event_from_selection(self, start_time, end_time):
        """
        Add an event from interactive plot selection.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
        """
        # Generate unique name
        event_num = len([e for e in self.events if e.name.startswith("Event")]) + 1
        name = f"Event {event_num}"
        
        # Validate times
        if start_time < self.min_time:
            start_time = self.min_time
        if end_time > self.max_time:
            end_time = self.max_time
        if start_time >= end_time:
            start_time, end_time = end_time, start_time
        
        event = Event(name, start_time, end_time)
        self.events.append(event)
        self._update_table()
    
    def set_max_time(self, max_time):
        """Update maximum time value."""
        self.max_time = float(max_time)
        if self.max_time <= self.min_time:
            self.max_time = self.min_time + 1.0
        
        # Update "Full" event if it exists
        if self.events and self.events[0].name == "Full":
            self.events[0].start_time = self.min_time
            self.events[0].end_time = self.max_time
            self._update_table()

    def set_time_bounds(self, min_time, max_time):
        """Update minimum and maximum time bounds."""
        self.min_time = float(min_time)
        self.max_time = float(max_time)
        if self.max_time <= self.min_time:
            self.max_time = self.min_time + 1.0
        
        # Update "Full" event if it exists
        if self.events and self.events[0].name == "Full":
            self.events[0].start_time = self.min_time
            self.events[0].end_time = self.max_time
            self._update_table()

    def clear_all_events(self):
        """Clear all events except the 'Full' event."""
        # Keep only the "Full" event if it exists
        self.events = [e for e in self.events if e.name == "Full"]
        
        # Update table
        self._update_table()
        
        # Emit events updated signal
        self.events_updated.emit(self.events)
