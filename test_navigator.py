"""
Test Application for Enhanced Flight Navigator

This script tests the enhanced flight navigator with the large test HDF5 file.

Usage:
    python test_navigator.py

Author: SpectralEdge Development Team
Date: 2026-01-27
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.gui.flight_navigator import FlightNavigator


class TestWindow(QMainWindow):
    """Test window for flight navigator."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flight Navigator Test")
        self.resize(400, 200)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Info label
        info = QLabel("Click the button below to open the Enhanced Flight Navigator")
        layout.addWidget(info)
        
        # Open navigator button
        open_btn = QPushButton("Open Flight Navigator")
        open_btn.clicked.connect(self.open_navigator)
        layout.addWidget(open_btn)
        
        # Selection result label
        self.result_label = QLabel("No selection yet")
        layout.addWidget(self.result_label)
        
        # Load HDF5 file
        try:
            self.loader = HDF5FlightDataLoader('data/large_test_flight_data.hdf5')
            info.setText(f"Loaded: {len(self.loader.get_flights())} flights, "
                        f"{sum(len(self.loader.get_channels(f.flight_key)) for f in self.loader.get_flights())} total channels")
        except Exception as e:
            info.setText(f"Error loading HDF5 file: {e}")
            open_btn.setEnabled(False)
    
    def open_navigator(self):
        """Open the flight navigator dialog."""
        navigator = FlightNavigator(self.loader, self)
        navigator.data_selected.connect(self.on_data_selected)
        navigator.exec()
    
    def on_data_selected(self, selected_items):
        """Handle data selection from navigator."""
        count = len(selected_items)
        self.result_label.setText(f"Selected {count} channels:\n" + 
                                 "\n".join([f"  - {f}: {c}" for f, c, _ in selected_items[:5]]) +
                                 (f"\n  ... and {count-5} more" if count > 5 else ""))


def main():
    """Run test application."""
    app = QApplication(sys.argv)
    
    # Apply dark theme
    app.setStyle('Fusion')
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
