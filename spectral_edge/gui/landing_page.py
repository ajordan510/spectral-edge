"""
Landing Page GUI for SpectralEdge.

This module provides the main landing page interface where users can
select from available signal processing tools. The design is modular
to allow easy addition of new tools over time.

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor


class LandingPage(QMainWindow):
    """
    Main landing page window for SpectralEdge.
    
    This class creates the primary interface that users see when launching
    the application. It displays available tools as clickable cards in a
    grid layout.
    """
    
    def __init__(self):
        """
        Initialize the landing page window.
        
        Sets up the window properties, styling, and creates the main
        interface layout.
        """
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("SpectralEdge - Signal Processing Suite")
        self.setMinimumSize(1000, 700)
        
        # Apply aerospace-inspired styling
        self._apply_styling()
        
        # Create the main interface
        self._create_ui()
    
    def _apply_styling(self):
        """
        Apply custom styling to the application.
        
        This method sets up a professional, aerospace-inspired color scheme
        with dark blues, grays, and accent colors reminiscent of aerospace
        engineering tools.
        """
        # Define color palette (aerospace-inspired: dark blues and grays)
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
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d4758;
                border: 2px solid #5a6578;
            }
            QPushButton:pressed {
                background-color: #1d2738;
            }
            QFrame {
                background-color: #252d3d;
                border-radius: 10px;
            }
        """)
    
    def _create_ui(self):
        """
        Create the user interface layout.
        
        This method builds the main layout including the header, tool grid,
        and footer sections.
        """
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Create header section
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Create tools grid section
        tools_grid = self._create_tools_grid()
        main_layout.addWidget(tools_grid, stretch=1)
        
        # Create footer section
        footer = self._create_footer()
        main_layout.addWidget(footer)
    
    def _create_header(self):
        """
        Create the header section of the landing page.
        
        Returns:
            QFrame: A frame containing the application title and subtitle.
        """
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Application title
        title_label = QLabel("SpectralEdge")
        title_font = QFont("Arial", 36, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #60a5fa;")  # Aerospace blue accent
        
        # Subtitle
        subtitle_label = QLabel("Professional Signal Processing Suite")
        subtitle_font = QFont("Arial", 14)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #9ca3af;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        return header_frame
    
    def _create_tools_grid(self):
        """
        Create the grid of available tools.
        
        This method creates a grid layout containing cards for each available
        signal processing tool. Currently shows placeholder tools that will
        be implemented in future epics.
        
        Returns:
            QFrame: A frame containing the tools grid.
        """
        tools_frame = QFrame()
        tools_layout = QGridLayout(tools_frame)
        tools_layout.setSpacing(20)
        
        # Define available tools (placeholders for future epics)
        tools = [
            {
                "name": "PSD Analysis",
                "description": "Power Spectral Density\nwith Welch's Method",
                "icon": "📊"
            },
            {
                "name": "SRS Analysis",
                "description": "Shock Response\nSpectrum Calculator",
                "icon": "📈"
            },
            {
                "name": "SPL Analysis",
                "description": "Sound Pressure\nLevel Analyzer",
                "icon": "🔊"
            },
            {
                "name": "FDS Analysis",
                "description": "Fatigue Damage\nSpectrum Tool",
                "icon": "⚙️"
            },
            {
                "name": "VRS Analysis",
                "description": "Vibration Response\nSpectrum Calculator",
                "icon": "📉"
            },
            {
                "name": "Batch Processing",
                "description": "Process Multiple\nFiles Automatically",
                "icon": "⚡"
            }
        ]
        
        # Create tool cards in a grid (3 columns)
        row = 0
        col = 0
        for tool in tools:
            tool_card = self._create_tool_card(
                tool["name"], 
                tool["description"], 
                tool["icon"]
            )
            tools_layout.addWidget(tool_card, row, col)
            
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        return tools_frame
    
    def _create_tool_card(self, name, description, icon):
        """
        Create a card widget for a single tool.
        
        Args:
            name (str): The name of the tool.
            description (str): A brief description of the tool.
            icon (str): An emoji or icon representing the tool.
        
        Returns:
            QPushButton: A button styled as a card for the tool.
        """
        # Create button as a card
        card = QPushButton()
        card.setMinimumSize(250, 150)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create layout for card content
        card_layout = QVBoxLayout()
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon label
        icon_label = QLabel(icon)
        icon_font = QFont("Arial", 32)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Name label
        name_label = QLabel(name)
        name_font = QFont("Arial", 14, QFont.Weight.Bold)
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Description label
        desc_label = QLabel(description)
        desc_font = QFont("Arial", 10)
        desc_label.setFont(desc_font)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #9ca3af;")
        
        # Add labels to layout
        card_layout.addWidget(icon_label)
        card_layout.addWidget(name_label)
        card_layout.addWidget(desc_label)
        
        # Set layout to card
        card.setLayout(card_layout)
        
        # Connect click event (placeholder for now)
        card.clicked.connect(lambda: self._on_tool_clicked(name))
        
        return card
    
    def _create_footer(self):
        """
        Create the footer section of the landing page.
        
        Returns:
            QFrame: A frame containing footer information.
        """
        footer_frame = QFrame()
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Version info
        version_label = QLabel("Version 0.1.0 (Epic 1)")
        version_font = QFont("Arial", 10)
        version_label.setFont(version_font)
        version_label.setStyleSheet("color: #6b7280;")
        
        footer_layout.addWidget(version_label)
        
        return footer_frame
    
    def _on_tool_clicked(self, tool_name):
        """
        Handle tool card click events.
        
        This method is called when a user clicks on a tool card. Currently
        it's a placeholder that will be expanded in future epics to launch
        the appropriate tool interface.
        
        Args:
            tool_name (str): The name of the tool that was clicked.
        """
        # Placeholder: Print to console (will be replaced with actual tool launch)
        print(f"Tool clicked: {tool_name}")
        # TODO: Implement tool launching in future epics
