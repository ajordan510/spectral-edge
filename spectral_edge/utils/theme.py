"""Shared theme utilities for SpectralEdge GUI components."""

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
    QMenu::separator {
        background-color: #e2e8f0;
        height: 1px;
        margin: 2px 0;
    }
"""


def apply_context_menu_style(plot_widget):
    """Apply a light-themed context menu stylesheet to a pyqtgraph PlotWidget."""
    plot_widget.setStyleSheet(CONTEXT_MENU_STYLESHEET)
