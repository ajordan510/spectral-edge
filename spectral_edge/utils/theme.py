"""Shared theme utilities for SpectralEdge GUI components."""

import math

from PyQt6 import QtCore, sip
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

CONTEXT_MENU_THEME_MARKER = "/* spectral_edge_context_menu_theme */"
PYQTGRAPH_TOOL_THEME_MARKER = "/* spectral_edge_pyqtgraph_tool_theme */"
PYQTGRAPH_EXPORT_DIALOG_OBJECT_NAME = "pyqtgraphExportDialog"

CONTEXT_MENU_STYLESHEET = f"""
{CONTEXT_MENU_THEME_MARKER}
QMenu {{
    background-color: #1f2937;
    color: #e5e7eb;
    border: 1px solid #4a5568;
    border-radius: 6px;
    padding: 6px;
    margin: 0px;
}}
QMenu::item {{
    background-color: transparent;
    color: #e5e7eb;
    padding: 6px 30px 6px 30px;
    margin: 1px 4px;
    border: 1px solid transparent;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: #2563eb;
    color: #ffffff;
    border-color: #3b82f6;
}}
QMenu::item:pressed {{
    background-color: #1d4ed8;
    color: #ffffff;
}}
QMenu::item:disabled {{
    color: #6b7280;
    background-color: transparent;
}}
QMenu::item:selected:disabled {{
    color: #9ca3af;
    background-color: #374151;
    border-color: #4b5563;
}}
QMenu::separator {{
    height: 1px;
    background-color: #4b5563;
    margin: 5px 10px;
}}
QMenu::icon {{
    padding-left: 4px;
}}
QMenu::indicator {{
    width: 14px;
    height: 14px;
    margin-left: 6px;
    margin-right: 8px;
}}
QMenu::indicator:non-exclusive:unchecked,
QMenu::indicator:exclusive:unchecked {{
    border: 1px solid #6b7280;
    border-radius: 3px;
    background-color: #111827;
}}
QMenu::indicator:non-exclusive:unchecked:disabled,
QMenu::indicator:exclusive:unchecked:disabled {{
    border-color: #4b5563;
    background-color: #1f2937;
}}
QMenu::indicator:non-exclusive:checked {{
    border: 1px solid #60a5fa;
    border-radius: 3px;
    background-color: #60a5fa;
}}
QMenu::indicator:non-exclusive:checked:disabled {{
    border: 1px solid #4b5563;
    background-color: #4b5563;
}}
QMenu::indicator:exclusive:unchecked {{
    border-radius: 7px;
}}
QMenu::indicator:exclusive:checked {{
    border: 1px solid #60a5fa;
    border-radius: 7px;
    background-color: #60a5fa;
}}
QMenu::indicator:exclusive:checked:disabled {{
    border: 1px solid #4b5563;
    border-radius: 7px;
    background-color: #4b5563;
}}
QMenu::right-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-top: 5px solid transparent;
    border-bottom: 5px solid transparent;
    border-left: 6px solid #9ca3af;
    margin-right: 8px;
}}
QMenu::right-arrow:selected {{
    border-left-color: #ffffff;
}}
QMenu::left-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-top: 5px solid transparent;
    border-bottom: 5px solid transparent;
    border-right: 6px solid #9ca3af;
    margin-left: 8px;
}}
QMenu::left-arrow:selected {{
    border-right-color: #ffffff;
}}
QMenu::scroller {{
    background: #2d3748;
    height: 16px;
}}
QMenu::tearoff {{
    background: #4b5563;
    height: 1px;
}}

QMenu QWidget {{
    color: #e5e7eb;
    background-color: transparent;
}}
QMenu QLabel {{
    color: #e5e7eb;
    background-color: transparent;
}}
QMenu QFrame {{
    background-color: transparent;
    border: none;
}}
QMenu QGroupBox {{
    color: #e5e7eb;
    border: 1px solid #4b5563;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 6px;
}}
QMenu QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QMenu QListWidget {{
    background-color: #111827;
    color: #e5e7eb;
    border: 1px solid #4b5563;
    border-radius: 4px;
}}
QMenu QListWidget::item:selected {{
    background-color: #2563eb;
    color: #ffffff;
}}

QMenu QLineEdit,
QMenu QSpinBox,
QMenu QDoubleSpinBox,
QMenu QComboBox {{
    background-color: #111827;
    color: #e5e7eb;
    border: 1px solid #4b5563;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 20px;
}}
QMenu QLineEdit:disabled,
QMenu QSpinBox:disabled,
QMenu QDoubleSpinBox:disabled,
QMenu QComboBox:disabled {{
    color: #9ca3af;
    background-color: #1f2937;
    border-color: #374151;
}}
QMenu QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QMenu QComboBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #d1d5db;
}}
QMenu QComboBox QAbstractItemView {{
    background-color: #111827;
    color: #e5e7eb;
    border: 1px solid #4b5563;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}}

QMenu QSpinBox::up-button,
QMenu QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px;
    border-left: 1px solid #4b5563;
    border-bottom: 1px solid #4b5563;
    background-color: #374151;
}}
QMenu QSpinBox::down-button,
QMenu QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px;
    border-left: 1px solid #4b5563;
    background-color: #374151;
}}
QMenu QSpinBox::up-arrow,
QMenu QDoubleSpinBox::up-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 6px solid #d1d5db;
}}
QMenu QSpinBox::down-arrow,
QMenu QDoubleSpinBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #d1d5db;
}}

QMenu QCheckBox,
QMenu QRadioButton {{
    color: #e5e7eb;
    spacing: 8px;
    padding: 2px 0;
}}
QMenu QCheckBox::indicator,
QMenu QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid #6b7280;
    background-color: #111827;
}}
QMenu QCheckBox::indicator {{
    border-radius: 3px;
}}
QMenu QRadioButton::indicator {{
    border-radius: 7px;
}}
QMenu QCheckBox::indicator:checked,
QMenu QRadioButton::indicator:checked {{
    background-color: #60a5fa;
    border-color: #60a5fa;
}}
QMenu QCheckBox::indicator:disabled,
QMenu QRadioButton::indicator:disabled {{
    border-color: #4b5563;
    background-color: #1f2937;
}}

QMenu QSlider::groove:horizontal {{
    background-color: #374151;
    border: 1px solid #4b5563;
    height: 4px;
    border-radius: 2px;
}}
QMenu QSlider::handle:horizontal {{
    background-color: #60a5fa;
    border: 1px solid #3b82f6;
    width: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}
QMenu QSlider::sub-page:horizontal {{
    background-color: #3b82f6;
}}

QMenu QPushButton {{
    background-color: #2d3748;
    color: #e5e7eb;
    border: 1px solid #4b5563;
    border-radius: 4px;
    padding: 4px 10px;
}}
QMenu QPushButton:hover {{
    background-color: #3d4758;
    border-color: #5a6578;
}}
"""


def _build_pyqtgraph_tool_stylesheet(object_name: str) -> str:
    """Build an object-scoped dark stylesheet for pyqtgraph tool windows."""
    root_selector = f"QWidget#{object_name}"
    return f"""
{PYQTGRAPH_TOOL_THEME_MARKER}
{root_selector} {{
    background-color: #1a1f2e;
    color: #e0e0e0;
    border: 1px solid #4a5568;
    border-radius: 6px;
}}
{root_selector} QLabel {{
    color: #e0e0e0;
    background-color: transparent;
}}
{root_selector} QPushButton {{
    background-color: #2d3748;
    color: #e0e0e0;
    border: 1px solid #4a5568;
    border-radius: 4px;
    padding: 6px 12px;
}}
{root_selector} QPushButton:hover {{
    background-color: #3d4758;
    border-color: #5a6578;
}}
{root_selector} QPushButton:pressed {{
    background-color: #1d2738;
}}
{root_selector} QPushButton:disabled {{
    color: #9ca3af;
    background-color: #252d3d;
    border-color: #374151;
}}
{root_selector} QTreeWidget,
{root_selector} QListWidget,
{root_selector} QTreeView,
{root_selector} QAbstractItemView {{
    background-color: #0f172a;
    color: #e0e0e0;
    border: 1px solid #4a5568;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    outline: 0;
}}
{root_selector} QTreeWidget::item,
{root_selector} QListWidget::item {{
    padding: 3px 6px;
}}
{root_selector} QTreeWidget::item:hover,
{root_selector} QListWidget::item:hover {{
    background-color: #1f2937;
}}
{root_selector} QTreeWidget::item:selected,
{root_selector} QListWidget::item:selected {{
    background-color: #2563eb;
    color: #ffffff;
}}
{root_selector} QHeaderView::section {{
    background-color: #1f2937;
    color: #e0e0e0;
    border: 1px solid #374151;
    padding: 4px 6px;
}}
{root_selector} QLineEdit,
{root_selector} QSpinBox,
{root_selector} QDoubleSpinBox,
{root_selector} QComboBox {{
    background-color: #111827;
    color: #e0e0e0;
    border: 1px solid #4a5568;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 20px;
}}
{root_selector} QComboBox QAbstractItemView {{
    background-color: #111827;
    color: #e0e0e0;
    border: 1px solid #4a5568;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}}
{root_selector} QCheckBox,
{root_selector} QRadioButton {{
    color: #e0e0e0;
    spacing: 8px;
}}
{root_selector} QCheckBox::indicator,
{root_selector} QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid #4a5568;
    background-color: #1f2937;
}}
{root_selector} QCheckBox::indicator {{
    border-radius: 3px;
}}
{root_selector} QRadioButton::indicator {{
    border-radius: 7px;
}}
{root_selector} QCheckBox::indicator:checked,
{root_selector} QRadioButton::indicator:checked {{
    background-color: #60a5fa;
    border-color: #60a5fa;
}}
{root_selector} QScrollBar:vertical {{
    background: #1f2937;
    width: 12px;
    margin: 0px;
}}
{root_selector} QScrollBar::handle:vertical {{
    background: #4a5568;
    min-height: 20px;
    border-radius: 6px;
}}
{root_selector} QScrollBar:horizontal {{
    background: #1f2937;
    height: 12px;
    margin: 0px;
}}
{root_selector} QScrollBar::handle:horizontal {{
    background: #4a5568;
    min-width: 20px;
    border-radius: 6px;
}}
"""


PYQTGRAPH_TOOL_STYLESHEET = _build_pyqtgraph_tool_stylesheet(PYQTGRAPH_EXPORT_DIALOG_OBJECT_NAME)

_MENU_STYLE_EVENTS = {
    QtCore.QEvent.Type.Polish,
    QtCore.QEvent.Type.PolishRequest,
    QtCore.QEvent.Type.Show,
    QtCore.QEvent.Type.ChildAdded,
}

_TOOL_WINDOW_STYLE_EVENTS = {
    QtCore.QEvent.Type.Polish,
    QtCore.QEvent.Type.PolishRequest,
    QtCore.QEvent.Type.Show,
}


def get_context_menu_stylesheet() -> str:
    """Return the canonical global context-menu stylesheet."""
    return CONTEXT_MENU_STYLESHEET


def get_pyqtgraph_tool_stylesheet() -> str:
    """Return the canonical stylesheet for pyqtgraph tool windows."""
    return PYQTGRAPH_TOOL_STYLESHEET


def _is_qobject_alive(obj) -> bool:
    """Return True when a Qt object wrapper still owns a live C++ object."""
    if obj is None:
        return False
    try:
        return not sip.isdeleted(obj)
    except Exception:
        return False


def _is_pyqtgraph_export_dialog(widget: QWidget) -> bool:
    """Return True when widget is pyqtgraph's ExportDialog."""
    if widget is None:
        return False
    widget_class = widget.__class__
    return (
        widget_class.__name__ == "ExportDialog"
        and widget_class.__module__.startswith("pyqtgraph.GraphicsScene.exportDialog")
    )


def _set_export_dialog_defaults(widget: QWidget) -> None:
    """Set default exporter selection and initial geometry for pyqtgraph ExportDialog."""
    if not _is_qobject_alive(widget):
        return

    ui = getattr(widget, "ui", None)
    format_list = getattr(ui, "formatList", None)

    if format_list is not None:
        scene = getattr(widget, "scene", None)
        has_attached_view = scene is not None and hasattr(scene, "views") and len(scene.views()) > 0
        if format_list.count() == 0 and has_attached_view and hasattr(widget, "updateItemList"):
            widget.updateItemList()
        image_row = None
        for row in range(format_list.count()):
            item = format_list.item(row)
            if item is not None and "image file" in (item.text() or "").lower():
                image_row = row
                break
        if image_row is not None and format_list.currentRow() != image_row:
            format_list.setCurrentRow(image_row)

    base_height = getattr(widget, "_spectral_edge_export_base_height", None)
    if not isinstance(base_height, int) or base_height <= 0:
        size_hint_h = int(widget.sizeHint().height())
        base_height = max(int(widget.height()), int(widget.minimumHeight()), size_hint_h, 1)
        widget._spectral_edge_export_base_height = base_height

    target_height = max(base_height, int(math.ceil(base_height * 1.25)))
    widget._spectral_edge_export_target_height = target_height
    if widget.minimumHeight() < target_height:
        widget.setMinimumHeight(target_height)
    target_width = max(int(widget.width()), int(widget.minimumWidth()), int(widget.sizeHint().width()))
    if widget.height() < target_height:
        widget.resize(target_width, target_height)


def _apply_pyqtgraph_tool_window_style(widget: QWidget) -> None:
    """Apply scoped dark styling to pyqtgraph export/tool windows."""
    if not _is_qobject_alive(widget):
        return
    if not _is_pyqtgraph_export_dialog(widget):
        return

    try:
        if widget.objectName() != PYQTGRAPH_EXPORT_DIALOG_OBJECT_NAME:
            widget.setObjectName(PYQTGRAPH_EXPORT_DIALOG_OBJECT_NAME)

        current_stylesheet = widget.styleSheet() or ""
        if PYQTGRAPH_TOOL_THEME_MARKER not in current_stylesheet:
            widget.setStyleSheet(f"{current_stylesheet}\n{PYQTGRAPH_TOOL_STYLESHEET}".strip())
        _set_export_dialog_defaults(widget)
    except RuntimeError:
        # Widget can be deleted while the event filter is processing.
        return


def _apply_menu_tree_style(menu: QMenu) -> None:
    """Apply stylesheet and hooks to a menu plus all nested submenus."""
    if not _is_qobject_alive(menu):
        return

    try:
        if CONTEXT_MENU_THEME_MARKER not in (menu.styleSheet() or ""):
            menu.setStyleSheet(CONTEXT_MENU_STYLESHEET)

        if not getattr(menu, "_spectral_edge_menu_hooked", False):
            menu.aboutToShow.connect(lambda m=menu: _apply_menu_tree_style(m))
            menu._spectral_edge_menu_hooked = True

        for action in list(menu.actions()):
            child_menu = action.menu()
            if _is_qobject_alive(child_menu):
                _apply_menu_tree_style(child_menu)

        for child_menu in list(menu.findChildren(QMenu)):
            if _is_qobject_alive(child_menu):
                _apply_menu_tree_style(child_menu)
    except RuntimeError:
        # Qt can destroy transient menus between queued events.
        return


class _GlobalThemeStyleFilter(QtCore.QObject):
    """Event filter that styles menus and tool windows at runtime."""

    def eventFilter(self, watched, event):  # noqa: N802 (Qt API signature)
        try:
            if isinstance(watched, QMenu) and event.type() in _MENU_STYLE_EVENTS:
                _apply_menu_tree_style(watched)
            elif isinstance(watched, QWidget) and event.type() in _TOOL_WINDOW_STYLE_EVENTS:
                _apply_pyqtgraph_tool_window_style(watched)
        except RuntimeError:
            # Ignore stale wrapped objects emitted during teardown.
            pass
        return super().eventFilter(watched, event)


def install_global_context_menu_style(app=None) -> None:
    """
    Install global context-menu and pyqtgraph tool-window styling.

    This function is idempotent and safe to call repeatedly.
    """
    target_app = app or QApplication.instance()
    if target_app is None:
        return

    merged_stylesheet = target_app.styleSheet() or ""
    if CONTEXT_MENU_THEME_MARKER not in merged_stylesheet:
        merged_stylesheet = f"{merged_stylesheet.rstrip()}\n\n{CONTEXT_MENU_STYLESHEET.strip()}".strip()
    if PYQTGRAPH_TOOL_THEME_MARKER not in merged_stylesheet:
        merged_stylesheet = f"{merged_stylesheet.rstrip()}\n\n{PYQTGRAPH_TOOL_STYLESHEET.strip()}".strip()
    if merged_stylesheet != (target_app.styleSheet() or ""):
        target_app.setStyleSheet(merged_stylesheet)

    if not getattr(target_app, "_spectral_edge_theme_filter_installed", False):
        theme_style_filter = _GlobalThemeStyleFilter(target_app)
        target_app.installEventFilter(theme_style_filter)
        target_app._spectral_edge_theme_filter = theme_style_filter
        target_app._spectral_edge_theme_filter_installed = True

    for existing_menu in target_app.findChildren(QMenu):
        _apply_menu_tree_style(existing_menu)

    for top_level_widget in target_app.topLevelWidgets():
        _apply_pyqtgraph_tool_window_style(top_level_widget)


def apply_context_menu_style(plot_widget):
    """Apply robust global menu styling while preserving call-site compatibility."""
    install_global_context_menu_style()
    if plot_widget is None:
        return

    plot_item = getattr(plot_widget, "plotItem", None)
    if plot_item is None and hasattr(plot_widget, "getPlotItem"):
        plot_item = plot_widget.getPlotItem()
    if plot_item is None:
        return

    view_box = plot_item.getViewBox() if hasattr(plot_item, "getViewBox") else None
    view_box_menu = getattr(view_box, "menu", None)
    if isinstance(view_box_menu, QMenu):
        _apply_menu_tree_style(view_box_menu)

    plot_item_menu = getattr(plot_item, "ctrlMenu", None)
    if isinstance(plot_item_menu, QMenu):
        _apply_menu_tree_style(plot_item_menu)


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
