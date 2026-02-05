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
