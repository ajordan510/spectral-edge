"""
Styled Message Box Utilities

This module provides styled QMessageBox functions with dark, readable text
that works consistently across all platforms, especially Windows.

The default QMessageBox on Windows can have very light text on white background,
making it nearly impossible to read. This module ensures all message boxes have
proper contrast.

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import QMessageBox, QWidget
from typing import Optional


# Message box stylesheet with dark text and proper contrast
MESSAGE_BOX_STYLE = """
QMessageBox {
    background-color: #f0f0f0;
}
QMessageBox QLabel {
    color: #000000;
    font-size: 13px;
    min-width: 250px;
    max-width: 500px;
    padding: 0px;
    margin: 0px;
}
QMessageBox QPushButton {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 13px;
    min-width: 80px;
}
QMessageBox QPushButton:hover {
    background-color: #106ebe;
}
QMessageBox QPushButton:pressed {
    background-color: #005a9e;
}
"""


def show_information(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show an information message box with readable styling.
    
    Args:
        parent: Parent widget (can be None)
        title: Title of the message box
        message: Message text to display
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStyleSheet(MESSAGE_BOX_STYLE)
    msg_box.exec()


def show_warning(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show a warning message box with readable styling.
    
    Args:
        parent: Parent widget (can be None)
        title: Title of the message box
        message: Message text to display
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStyleSheet(MESSAGE_BOX_STYLE)
    msg_box.exec()


def show_critical(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show a critical error message box with readable styling.
    
    Args:
        parent: Parent widget (can be None)
        title: Title of the message box
        message: Message text to display
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStyleSheet(MESSAGE_BOX_STYLE)
    msg_box.exec()


def show_question(parent: Optional[QWidget], title: str, message: str) -> bool:
    """
    Show a question message box with Yes/No buttons and readable styling.
    
    Args:
        parent: Parent widget (can be None)
        title: Title of the message box
        message: Question text to display
    
    Returns:
        True if user clicked Yes, False if user clicked No
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Question)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg_box.setDefaultButton(QMessageBox.StandardButton.No)
    msg_box.setStyleSheet(MESSAGE_BOX_STYLE)
    
    result = msg_box.exec()
    return result == QMessageBox.StandardButton.Yes
