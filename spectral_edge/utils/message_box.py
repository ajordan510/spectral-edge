"""
Styled Message Box Utilities

This module provides custom dialog boxes with clean, professional appearance.
No icons, simple box layout, extremely professional styling.

Features:
- Icon-free, single-column layout
- High contrast dark text on light background
- Clean, minimal design
- Tight spacing and professional appearance
- Word wrapping for long messages
- Consistent styling across platforms

Author: SpectralEdge Development Team
Date: 2026-01-29
"""

from PyQt6.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt
from typing import Optional


class CleanDialog(QDialog):
    """
    Clean, professional dialog without icons.
    
    Simple box layout with title, message, and buttons.
    Extremely professional appearance with tight spacing.
    """
    
    def __init__(self, parent: Optional[QWidget], title: str, message: str,
                 buttons: list = None, default_button: int = 0):
        """
        Initialize clean dialog.
        
        Parameters:
        -----------
        parent : QWidget, optional
            Parent widget
        title : str
            Dialog window title
        message : str
            Message text to display
        buttons : list of str, optional
            Button labels (default: ["OK"])
        default_button : int
            Index of default button (default: 0)
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.result_value = None
        
        # Professional styling - clean and minimal
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
            }
            QLabel {
                color: #1a1a1a;
                font-size: 14px;
                line-height: 1.6;
            }
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:default {
                background-color: #0063b1;
                font-weight: 600;
            }
        """)
        
        # Main layout with tight margins
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Message label
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setMinimumWidth(350)
        message_label.setMaximumWidth(600)
        message_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(message_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Create buttons
        if buttons is None:
            buttons = ["OK"]
        
        self.buttons = []
        for i, button_text in enumerate(buttons):
            btn = QPushButton(button_text)
            btn.clicked.connect(lambda checked, idx=i: self._on_button_clicked(idx))
            if i == default_button:
                btn.setDefault(True)
            button_layout.addWidget(btn)
            self.buttons.append(btn)
        
        layout.addLayout(button_layout)
        
        # Adjust size to content
        self.adjustSize()
        self.setFixedSize(self.sizeHint())
    
    def _on_button_clicked(self, index: int):
        """Handle button click."""
        self.result_value = index
        self.accept()
    
    def get_result(self) -> int:
        """Get the index of the clicked button."""
        return self.result_value if self.result_value is not None else 0


class CleanDetailDialog(QDialog):
    """
    Clean dialog with expandable details section.
    
    Used for errors with stack traces or detailed information.
    """
    
    def __init__(self, parent: Optional[QWidget], title: str, message: str,
                 details: Optional[str] = None):
        """
        Initialize clean detail dialog.
        
        Parameters:
        -----------
        parent : QWidget, optional
            Parent widget
        title : str
            Dialog window title
        message : str
            Main message to display
        details : str, optional
            Additional details (shown in scrollable area)
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMaximumWidth(800)
        
        # Professional styling
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
            }
            QLabel {
                color: #1a1a1a;
            }
            QTextEdit {
                background-color: #f8f8f8;
                color: #1a1a1a;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 11px;
                padding: 10px;
            }
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 500;
                min-width: 80px;
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
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Main message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 14px; line-height: 1.6;")
        layout.addWidget(message_label)
        
        # Details section (if provided)
        if details:
            details_label = QLabel("Details:")
            details_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #666666; margin-top: 8px;")
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
    Show an information dialog with clean, professional styling.
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the dialog window
    message : str
        Message text to display
    """
    dialog = CleanDialog(parent, title, message, buttons=["OK"])
    dialog.exec()


def show_warning(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show a warning dialog with clean, professional styling.
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the dialog window
    message : str
        Message text to display
    """
    dialog = CleanDialog(parent, title, message, buttons=["OK"])
    dialog.exec()


def show_critical(parent: Optional[QWidget], title: str, message: str, 
                  details: Optional[str] = None) -> None:
    """
    Show a critical error dialog with clean, professional styling.
    
    For simple errors, uses CleanDialog.
    For errors with details, uses CleanDetailDialog.
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the dialog window
    message : str
        Message text to display
    details : str, optional
        Additional error details (e.g., stack trace)
    """
    if details:
        dialog = CleanDetailDialog(parent, title, message, details)
        dialog.exec()
    else:
        dialog = CleanDialog(parent, title, message, buttons=["OK"])
        dialog.exec()


def show_error(parent: Optional[QWidget], title: str, message: str,
               exception: Optional[Exception] = None) -> None:
    """
    Show an error dialog with optional exception details.
    
    This is a convenience function that formats exception information
    for display in the detail dialog.
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the dialog window
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
    
    dialog = CleanDetailDialog(parent, title, message, details)
    dialog.exec()


def show_question(parent: Optional[QWidget], title: str, message: str) -> bool:
    """
    Show a question dialog with Yes/No buttons and clean, professional styling.
    
    Parameters:
    -----------
    parent : QWidget, optional
        Parent widget (can be None)
    title : str
        Title of the dialog window
    message : str
        Question text to display
    
    Returns:
    --------
    bool
        True if user clicked Yes, False if user clicked No
    """
    dialog = CleanDialog(parent, title, message, buttons=["No", "Yes"], default_button=0)
    dialog.exec()
    # Button index: 0 = No, 1 = Yes
    return dialog.get_result() == 1
