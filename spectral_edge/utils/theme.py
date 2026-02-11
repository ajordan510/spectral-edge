"""Shared theme utilities for SpectralEdge GUI components."""

from PyQt6.QtWidgets import QMenu

CONTEXT_MENU_STYLESHEET = """
    QMenu {
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
    }
    QMenu::item {
        padding: 6px 20px;
    }
    QMenu::item:selected {
        background-color: #3b82f6;
        color: #ffffff;
    }
    QMenu::item:disabled {
        color: #475569;
    }
    QMenu::separator {
        background-color: #e2e8f0;
        height: 1px;
        margin: 2px 0;
    }
    QMenu QLineEdit, QMenu QSpinBox, QMenu QDoubleSpinBox {
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #cbd5e1;
        border-radius: 3px;
        padding: 4px 6px;
        min-height: 20px;
    }
    QMenu QComboBox {
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #cbd5e1;
        border-radius: 3px;
        padding: 4px 6px;
        min-height: 20px;
    }
    QMenu QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #1e293b;
        selection-background-color: #3b82f6;
        selection-color: #ffffff;
        border: 1px solid #cbd5e1;
    }
    QMenu QCheckBox {
        color: #1e293b;
        spacing: 6px;
    }
    QMenu QCheckBox::indicator {
        width: 14px;
        height: 14px;
        border: 1px solid #cbd5e1;
        border-radius: 2px;
        background-color: #ffffff;
    }
    QMenu QCheckBox::indicator:checked {
        background-color: #3b82f6;
        border-color: #3b82f6;
    }
    QMenu QAbstractButton {
        color: #1e293b;
    }
    QMenu QGroupBox {
        color: #1e293b;
        background-color: transparent;
    }
    QMenu QLabel {
        color: #1e293b;
        background-color: transparent;
    }
    QMenu QWidget {
        color: #1e293b;
    }
"""


def apply_context_menu_style(plot_widget):
    """Apply a light-themed context menu stylesheet to a pyqtgraph PlotWidget."""
    plot_widget.setStyleSheet(CONTEXT_MENU_STYLESHEET)

    view_box = plot_widget.getPlotItem().getViewBox()
    menu = getattr(view_box, "menu", None)
    if menu is None:
        return

    def apply_menu_styles(target_menu):
        target_menu.setStyleSheet(CONTEXT_MENU_STYLESHEET)
        for action in target_menu.actions():
            child_menu = action.menu()
            if child_menu is not None:
                apply_menu_styles(child_menu)
        for child_menu in target_menu.findChildren(QMenu):
            child_menu.setStyleSheet(CONTEXT_MENU_STYLESHEET)
            if not getattr(child_menu, "_spectral_edge_menu_hooked", False):
                child_menu.aboutToShow.connect(lambda m=child_menu: apply_menu_styles(m))
                child_menu._spectral_edge_menu_hooked = True

    apply_menu_styles(menu)
    if not getattr(menu, "_spectral_edge_menu_hooked", False):
        menu.aboutToShow.connect(lambda: apply_menu_styles(menu))
        menu._spectral_edge_menu_hooked = True


def _build_dark_dialog_stylesheet(object_name: str) -> str:
    """Build an object-scoped dark-theme stylesheet for dialogs."""
    root_selector = f"QDialog#{object_name}"
    return f"""
/* spectral_edge_dark_dialog_theme */
{root_selector} {{
    background-color: #1a1f2e;
    color: #e0e0e0;
}}
{root_selector} QLabel {{
    color: #e0e0e0;
    background-color: transparent;
}}
{root_selector} QGroupBox {{
    color: #e0e0e0;
    border: 2px solid #4a5568;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
    padding-top: 6px;
}}
{root_selector} QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px 0 5px;
}}
{root_selector} QPushButton {{
    background-color: #2d3748;
    color: #e0e0e0;
    border: 1px solid #4a5568;
    border-radius: 4px;
    padding: 6px 14px;
}}
{root_selector} QPushButton:hover {{
    background-color: #3d4758;
    border-color: #5a6578;
}}
{root_selector} QPushButton:pressed {{
    background-color: #1d2738;
}}
{root_selector} QComboBox,
{root_selector} QSpinBox,
{root_selector} QDoubleSpinBox,
{root_selector} QLineEdit {{
    background-color: #2d3748;
    color: #e0e0e0;
    border: 1px solid #4a5568;
    border-radius: 3px;
    padding: 4px 8px;
    min-height: 20px;
}}
{root_selector} QComboBox QAbstractItemView {{
    background-color: #1f2937;
    color: #e0e0e0;
    border: 1px solid #4a5568;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}}
{root_selector} QCheckBox {{
    color: #e0e0e0;
    spacing: 8px;
}}
{root_selector} QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #4a5568;
    border-radius: 3px;
    background-color: #2d3748;
}}
{root_selector} QCheckBox::indicator:checked {{
    background-color: #60a5fa;
    border-color: #60a5fa;
}}
{root_selector} QScrollArea,
{root_selector} QListWidget {{
    background-color: #1a1f2e;
    border: 1px solid #4a5568;
}}
{root_selector} QToolTip {{
    color: #ffffff;
    background-color: #111827;
    border: 1px solid #4a5568;
}}
"""


def apply_dark_dialog_theme(dialog, object_name: str = "darkDialog") -> None:
    """
    Apply a robust dark theme to a dialog using object-scoped selectors.

    The scoped selector prevents parent or global dialog styles from forcing
    an unintended light background.
    """
    dialog.setObjectName(object_name)
    marker = "/* spectral_edge_dark_dialog_theme */"
    scoped_stylesheet = _build_dark_dialog_stylesheet(object_name)
    current_stylesheet = dialog.styleSheet() or ""
    if marker in current_stylesheet:
        return
    dialog.setStyleSheet(f"{current_stylesheet}\n{scoped_stylesheet}".strip())
