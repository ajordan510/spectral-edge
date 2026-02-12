"""
Global Stylesheet Definitions for SpectralEdge

This module provides consistent styling across the application while ensuring
that dialog boxes (QMessageBox, QInputDialog, QFileDialog) remain readable
with light backgrounds and dark text.

Author: SpectralEdge Development Team
Date: 2026-02-04
"""

from spectral_edge.utils.theme import (
    get_context_menu_stylesheet,
    get_pyqtgraph_tool_stylesheet,
    install_global_context_menu_style,
)

# Aerospace-inspired dark theme for main windows
DARK_THEME = """
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
        padding: 8px 16px;
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
        margin-top: 12px;
        font-weight: bold;
        padding-top: 8px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px 0 5px;
    }
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
        background-color: #2d3748;
        color: #e0e0e0;
        border: 1px solid #4a5568;
        border-radius: 3px;
        padding: 5px;
        min-height: 20px;
    }
    QCheckBox {
        color: #e0e0e0;
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
        background-color: #60a5fa;
        border-color: #60a5fa;
    }
    QToolTip {
        color: #ffffff;
        background-color: #111827;
        border: 1px solid #4a5568;
        padding: 4px;
    }
"""

# Light, readable styling for dialog boxes
DIALOG_LIGHT_THEME = """
    QMessageBox {
        background-color: #ffffff;
    }
    QMessageBox QLabel {
        color: #1a1a1a;
        background-color: #ffffff;
        font-size: 11pt;
        padding: 10px;
    }
    QMessageBox QPushButton {
        background-color: #0078d4;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 8px 20px;
        font-size: 11pt;
        min-width: 80px;
    }
    QMessageBox QPushButton:hover {
        background-color: #106ebe;
    }
    QMessageBox QPushButton:pressed {
        background-color: #005a9e;
    }
    QMessageBox QPushButton:default {
        background-color: #0063b1;
        font-weight: 600;
    }
    
    QInputDialog {
        background-color: #ffffff;
    }
    QInputDialog QLabel {
        color: #1a1a1a;
        background-color: #ffffff;
        font-size: 11pt;
    }
    QInputDialog QLineEdit {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #d0d0d0;
        border-radius: 3px;
        padding: 6px;
        font-size: 11pt;
        min-width: 300px;
    }
    QInputDialog QPushButton {
        background-color: #0078d4;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 8px 20px;
        font-size: 11pt;
        min-width: 80px;
    }
    QInputDialog QPushButton:hover {
        background-color: #106ebe;
    }
"""

# Combined stylesheet for application
GLOBAL_STYLESHEET = (
    DARK_THEME
    + DIALOG_LIGHT_THEME
    + get_context_menu_stylesheet()
    + get_pyqtgraph_tool_stylesheet()
)


def apply_global_stylesheet(app):
    """
    Apply global stylesheet to the entire application.
    
    This ensures consistent styling across all windows while keeping
    dialog boxes readable with light backgrounds.
    
    Args:
        app: QApplication instance
    """
    app.setStyleSheet(GLOBAL_STYLESHEET)
    install_global_context_menu_style(app)


def get_dark_theme():
    """
    Get the dark theme stylesheet for main windows.
    
    Returns:
        str: Dark theme CSS stylesheet
    """
    return DARK_THEME


def get_dialog_theme():
    """
    Get the light theme stylesheet for dialog boxes.
    
    Returns:
        str: Light theme CSS stylesheet for dialogs
    """
    return DIALOG_LIGHT_THEME


def get_combined_stylesheet():
    """
    Get the combined stylesheet with both dark theme and readable dialogs.
    
    Returns:
        str: Combined CSS stylesheet
    """
    return GLOBAL_STYLESHEET
