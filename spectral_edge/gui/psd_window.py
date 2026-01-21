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
    QGroupBox, QGridLayout, QMessageBox, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from pathlib import Path

# Import our custom modules
from spectral_edge.utils.data_loader import load_csv_data, DataLoadError
from spectral_edge.core.psd import (
    calculate_psd_welch, psd_to_db, calculate_rms_from_psd, get_window_options
)
from spectral_edge.gui.spectrogram_window import SpectrogramWindow
from spectral_edge.gui.event_manager import EventManagerWindow, Event


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
        self.time_data = None
        self.signal_data = None
        self.channel_names = None
        self.channel_units = []  # Store units for each channel
        self.sample_rate = None
        self.current_file = None
        
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
            QComboBox, QSpinBox, QDoubleSpinBox {
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
        
        # File loading group
        file_group = self._create_file_group()
        layout.addWidget(file_group)
        
        # Channel selection group
        self.channel_group = self._create_channel_group()
        layout.addWidget(self.channel_group)
        
        # Frequency range group
        freq_range_group = self._create_frequency_range_group()
        layout.addWidget(freq_range_group)
        
        # Parameter configuration group
        param_group = self._create_parameter_group()
        layout.addWidget(param_group)
        
        # Display options group
        display_group = self._create_display_options_group()
        layout.addWidget(display_group)
        
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
        
        # Load file button
        load_button = QPushButton("Load CSV File")
        load_button.clicked.connect(self._load_file)
        layout.addWidget(load_button)
        
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
        scroll.setMaximumHeight(150)
        
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
        layout.addWidget(QLabel("Overlap (%):"), row, 0)
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(50)
        self.overlap_spin.setSingleStep(10)
        self.overlap_spin.valueChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.overlap_spin, row, 1)
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
        self.time_legend.setBrush(pg.mkBrush(26, 31, 46, 200))  # Semi-transparent GUI background
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
        self.legend.setBrush(pg.mkBrush(26, 31, 46, 200))  # Semi-transparent GUI background
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
        self.legend.setBrush(pg.mkBrush(26, 31, 46, 200))
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
            self.time_data, self.signal_data, self.channel_names, self.sample_rate = \
                load_csv_data(file_path)
            
            self.current_file = Path(file_path).name
            
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
            duration = len(self.time_data) / self.sample_rate
            info_text = (f"Channels: {num_channels}\n"
                        f"Sample Rate: {self.sample_rate:.1f} Hz\n"
                        f"Duration: {duration:.2f} s\n"
                        f"Samples: {len(self.time_data)}")
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
            QMessageBox.critical(self, "Error Loading File", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An error occurred: {e}")
    
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
        """Plot time history of selected channels."""
        if self.signal_data is None:
            return
        
        # Clear previous plot
        self.time_plot_widget.clear()
        self.time_legend.clear()
        
        # Re-add legend with styling
        self.time_legend = self.time_plot_widget.addLegend(offset=(10, 10))
        self.time_legend.setBrush(pg.mkBrush(26, 31, 46, 200))
        self.time_legend.setPen(pg.mkPen(74, 85, 104, 255))
        
        # Define colors for different channels
        colors = ['#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
        # Plot each selected channel
        plot_count = 0
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                channel_name = self.channel_names[i]
                signal = self.signal_data[i, :]
                
                # Plot the time history
                color = colors[plot_count % len(colors)]
                pen = pg.mkPen(color=color, width=1.5)
                self.time_plot_widget.plot(
                    self.time_data,
                    signal,
                    pen=pen,
                    name=channel_name
                )
                
                plot_count += 1
        
        # Update Y-axis label with units
        if self.channel_units and self.channel_units[0]:
            unit = self.channel_units[0]
            self.time_plot_widget.setLabel('left', f'Amplitude ({unit})', color='#e0e0e0', size='11pt')
        else:
            self.time_plot_widget.setLabel('left', 'Amplitude', color='#e0e0e0', size='11pt')
    
    def _calculate_psd(self):
        """Calculate PSD with current parameters for all channels."""
        if self.signal_data is None:
            return
        
        try:
            # Get parameters from UI
            window = self.window_combo.currentText().lower()
            df = self.df_spin.value()
            nperseg = int(self.sample_rate / df)
            
            if self.efficient_fft_checkbox.isChecked():
                nperseg = 2 ** int(np.ceil(np.log2(nperseg)))
            
            overlap_percent = self.overlap_spin.value()
            noverlap = int(nperseg * overlap_percent / 100)
            
            # Get frequency range for RMS calculation
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()
            
            # Calculate PSD for each channel
            num_channels = self.signal_data.shape[0]
            
            self.psd_results = {}
            self.rms_values = {}
            
            for channel_idx in range(num_channels):
                channel_name = self.channel_names[channel_idx]
                signal = self.signal_data[channel_idx, :]
                
                # Calculate PSD
                frequencies, psd = calculate_psd_welch(
                    signal,
                    self.sample_rate,
                    window=window,
                    nperseg=nperseg,
                    noverlap=noverlap
                )
                
                # Store full frequency range (same for all channels)
                if self.frequencies is None:
                    self.frequencies = frequencies
                
                # Store PSD for this channel
                self.psd_results[channel_name] = psd
                
                # Calculate RMS over specified frequency range
                # Create mask for RMS calculation
                rms_mask = (frequencies >= freq_min) & (frequencies <= freq_max)
                if np.any(rms_mask):
                    rms = calculate_rms_from_psd(frequencies[rms_mask], psd[rms_mask])
                else:
                    rms = 0.0
                
                self.rms_values[channel_name] = rms
            
            # Update plot
            self._update_plot()
            
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Failed to calculate PSD: {e}\n\nPlease try adjusting the frequency resolution or frequency range.")
    
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
            QMessageBox.warning(self, "No Data", "No frequency data in the specified range. Please adjust the frequency range.")
            return
        
        frequencies_plot = self.frequencies[freq_mask]
        
        # Define colors for different channels
        colors = ['#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
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
                
                # Create legend label with RMS
                if unit:
                    legend_label = f"{channel_name}: RMS={rms:.4f} {unit}"
                else:
                    legend_label = f"{channel_name}: RMS={rms:.4f}"
                
                # Plot the PSD
                color = colors[plot_count % len(colors)]
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
        
        # Set X-axis range to user-specified range
        self.plot_widget.setXRange(np.log10(freq_min), np.log10(freq_max))
        
        # Set custom frequency ticks (powers of 10 only)
        self._set_frequency_ticks()
        
        # Re-enable auto-range for user interaction, but keep current view
        self.plot_widget.getPlotItem().vb.enableAutoRange(enable=False)
    
    def _open_spectrogram(self):
        """Open spectrogram window for selected channel."""
        if self.signal_data is None:
            return
        
        # Find first selected channel
        selected_channel_idx = None
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                selected_channel_idx = i
                break
        
        if selected_channel_idx is None:
            QMessageBox.warning(self, "No Channel Selected", "Please select at least one channel to generate spectrogram.")
            return
        
        channel_name = self.channel_names[selected_channel_idx]
        signal = self.signal_data[selected_channel_idx, :]
        unit = self.channel_units[selected_channel_idx] if selected_channel_idx < len(self.channel_units) else ''
        
        # Get current PSD parameters to pass to spectrogram
        window = self.window_combo.currentText().lower()
        df = self.df_spin.value()
        overlap_percent = self.overlap_spin.value()
        efficient_fft = self.efficient_fft_checkbox.isChecked()
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Create or show spectrogram window
        if channel_name in self.spectrogram_windows:
            window_obj = self.spectrogram_windows[channel_name]
            window_obj.show()
            window_obj.raise_()
            window_obj.activateWindow()
        else:
            window_obj = SpectrogramWindow(
                self.time_data,
                signal,
                channel_name,
                self.sample_rate,
                unit,
                window_type=window,
                df=df,
                overlap_percent=overlap_percent,
                efficient_fft=efficient_fft,
                freq_min=freq_min,
                freq_max=freq_max
            )
            window_obj.show()
            self.spectrogram_windows[channel_name] = window_obj
    
    def _open_event_manager(self):
        """Open the Event Manager window."""
        if self.time_data is None:
            return
        
        # Create event manager if it doesn't exist
        if self.event_manager is None:
            max_time = self.time_data[-1]
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
        time_value = max(0, min(time_value, self.time_data[-1]))
        
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
        """Calculate PSDs for all defined events."""
        if self.signal_data is None or not self.events:
            return
        
        try:
            # Get parameters from UI
            window = self.window_combo.currentText().lower()
            df = self.df_spin.value()
            nperseg = int(self.sample_rate / df)
            
            if self.efficient_fft_checkbox.isChecked():
                nperseg = 2 ** int(np.ceil(np.log2(nperseg)))
            
            overlap_percent = self.overlap_spin.value()
            noverlap = int(nperseg * overlap_percent / 100)
            
            # Get frequency range for RMS calculation
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()
            
            # Clear previous results
            self.psd_results = {}
            self.rms_values = {}
            
            # Calculate PSD for each event and channel
            for event in self.events:
                # Get time indices for this event
                start_idx = int(event.start_time * self.sample_rate)
                end_idx = int(event.end_time * self.sample_rate)
                
                # Clamp to valid range
                start_idx = max(0, start_idx)
                end_idx = min(len(self.time_data), end_idx)
                
                if end_idx - start_idx < nperseg:
                    # Skip events that are too short
                    continue
                
                # Calculate PSD for each channel
                for channel_idx in range(self.signal_data.shape[0]):
                    channel_name = self.channel_names[channel_idx]
                    signal_segment = self.signal_data[channel_idx, start_idx:end_idx]
                    
                    # Calculate PSD
                    frequencies, psd = calculate_psd_welch(
                        signal_segment,
                        self.sample_rate,
                        window=window,
                        nperseg=nperseg,
                        noverlap=noverlap
                    )
                    
                    # Store full frequency range (same for all)
                    if self.frequencies is None:
                        self.frequencies = frequencies
                    
                    # Create unique key for event + channel
                    key = f"{event.name}_{channel_name}"
                    
                    # Store PSD for this event and channel
                    self.psd_results[key] = psd
                    
                    # Calculate RMS over specified frequency range
                    rms_mask = (frequencies >= freq_min) & (frequencies <= freq_max)
                    if np.any(rms_mask):
                        rms = calculate_rms_from_psd(frequencies[rms_mask], psd[rms_mask])
                    else:
                        rms = 0.0
                    
                    self.rms_values[key] = rms
            
            # Update plot
            self._update_plot_with_events()
            
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Failed to calculate event PSDs: {e}")
    
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
            QMessageBox.warning(self, "No Data", "No frequency data in the specified range.")
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
