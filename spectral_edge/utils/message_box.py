"""
Styled Message Box Utilities

This module provides styled QMessageBox functions with dark, readable text
that works consistently across all platforms, especially Windows.

The default QMessageBox on Windows can have very light text on white background,
making it nearly impossible to read. This module ensures all message boxes have
proper contrast and improved formatting.

Features:
- High contrast dark text on light background
- Larger, more readable fonts
- Word wrapping for long messages
- Proper spacing and padding
- Consistent styling across platforms

Author: SpectralEdge Development Team
Date: 2026-01-27
"""

from PyQt6.QtWidgets import QMessageBox, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
from typing import Optional


# Enhanced message box stylesheet with high contrast and better readability
MESSAGE_BOX_STYLE = """
QMessageBox {
    background-color: #ffffff;
    border: 1px solid #cccccc;
}
QMessageBox QLabel {
    color: #1a1a1a;
    font-size: 14px;
    font-weight: normal;
    min-width: 350px;
    max-width: 600px;
    padding: 8px;
    margin: 4px;
    line-height: 1.5;
}
QMessageBox QLabel#qt_msgbox_label {
    margin-left: 8px;
    padding-left: 8px;
    font-size: 14px;
}
QMessageBox QLabel#qt_msgboxinformativelabel {
    margin-left: 8px;
    padding-left: 8px;
    font-size: 13px;
    color: #333333;
}
QMessageBox QPushButton {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: bold;
    min-width: 90px;
}
QMessageBox QPushButton:hover {
    background-color: #106ebe;
}
QMessageBox QPushButton:pressed {
    background-color: #005a9e;
}
"""


class EnhancedErrorDialog(QDialog):
    """
    Enhanced error dialog with better formatting for long error messages.
    
    This dialog is used for critical errors and provides:
    - Large, readable title
    - Scrollable error details
    - Copy to clipboard functionality
    - Clear visual hierarchy
    """
    
    def __init__(self, parent: Optional[QWidget], title: str, message: str, 
                 details: Optional[str] = None, icon_type: str = "error"):
        """
        Initialize enhanced error dialog.
        
        Parameters:
        -----------
        parent : QWidget, optional
            Parent widget
        title : str
            Dialog title
        message : str
            Main message to display
        details : str, optional
            Additional details (shown in scrollable area)
        icon_type : str
            Type of icon: "error", "warning", "info", "question"
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMaximumWidth(800)
        
        # Apply styling
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                color: #1a1a1a;
            }
            QTextEdit {
                background-color: #f5f5f5;
                color: #1a1a1a;
                border: 1px solid #cccccc;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 8px;
            }
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton#copyBtn {
                background-color: #6c757d;
            }
            QPushButton#copyBtn:hover {
                background-color: #5a6268;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        
        # Icon
        icon_label = QLabel()
        icon_colors = {
            "error": "#dc3545",
            "warning": "#ffc107", 
            "info": "#17a2b8",
            "question": "#6f42c1"
        }
        icon_symbols = {
            "error": "✕",
            "warning": "⚠",
            "info": "ℹ",
            "question": "?"
        }
        icon_label.setText(icon_symbols.get(icon_type, "!"))
        icon_label.setStyleSheet(f"""
            QLabel {{
                color: {icon_colors.get(icon_type, '#dc3545')};
                font-size: 32px;
                font-weight: bold;
                min-width: 48px;
                max-width: 48px;
            }}
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #1a1a1a;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Main message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #333333;
                line-height: 1.6;
                padding: 8px 0;
            }
        """)
        layout.addWidget(message_label)
        
        # Details section (if provided)
        if details:
            details_label = QLabel("Details:")
            details_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    font-weight: bold;
                    color: #666666;
                    margin-top: 8px;
                }
            """)
            layout.addWidget(details_label)
            
            self.details_text = QTextEdit()
            self.details_text.setPlainText(details)
            self.details_text.setReadOnly(True)
            self.details_text.setMaximumHeight(200)
            layout.addWidget(self.details_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        if details:
            copy_btn = QPushButton("Copy Details")
            copy_btn.setObjectName("copyBtn")
            copy_btn.clicked.connect(self._copy_details)
            button_layout.addWidget(copy_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        self.details = details
    
    def _copy_details(self):
        """Copy error details to clipboard."""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.details or "")


def show_information(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show an information message box with readable styling.
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the message box
    message : str
        Message text to display
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
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the message box
    message : str
        Message text to display
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStyleSheet(MESSAGE_BOX_STYLE)
    msg_box.exec()


def show_critical(parent: Optional[QWidget], title: str, message: str, 
                  details: Optional[str] = None) -> None:
    """
    Show a critical error message box with enhanced formatting.
    
    For simple errors, uses standard QMessageBox.
    For errors with details, uses EnhancedErrorDialog for better readability.
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the message box
    message : str
        Message text to display
    details : str, optional
        Additional error details (e.g., stack trace)
    """
    if details:
        dialog = EnhancedErrorDialog(parent, title, message, details, "error")
        dialog.exec()
    else:
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStyleSheet(MESSAGE_BOX_STYLE)
        msg_box.exec()


def show_error(parent: Optional[QWidget], title: str, message: str,
               exception: Optional[Exception] = None) -> None:
    """
    Show an error dialog with optional exception details.
    
    This is a convenience function that formats exception information
    for display in the enhanced error dialog.
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the message box
    message : str
        Main error message
    exception : Exception, optional
        Exception object to extract details from
    """
    details = None
    if exception:
        import traceback
        details = f"Exception Type: {type(exception).__name__}\n"
        details += f"Exception Message: {str(exception)}\n\n"
        details += "Traceback:\n"
        details += traceback.format_exc()
    
    dialog = EnhancedErrorDialog(parent, title, message, details, "error")
    dialog.exec()


def show_question(parent: Optional[QWidget], title: str, message: str) -> bool:
    """
    Show a question message box with Yes/No buttons and readable styling.
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the message box
    message : str
        Question text to display
    
    Returns:
    --------
    bool
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
