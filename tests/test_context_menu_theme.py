import math
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")
pytest.importorskip("pyqtgraph")

import pyqtgraph as pg
from pyqtgraph.GraphicsScene.exportDialog import ExportDialog
from PyQt6.QtWidgets import QApplication, QMenu

from spectral_edge.gui.global_styles import apply_global_stylesheet
from spectral_edge.utils.theme import (
    CONTEXT_MENU_THEME_MARKER,
    PYQTGRAPH_EXPORT_DIALOG_OBJECT_NAME,
    PYQTGRAPH_TOOL_THEME_MARKER,
    _apply_menu_tree_style,
    apply_context_menu_style,
)


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_apply_context_menu_style_styles_viewbox_menu_and_submenus(app):
    plot_widget = pg.PlotWidget()
    apply_context_menu_style(plot_widget)
    app.processEvents()

    view_menu = plot_widget.getPlotItem().getViewBox().menu
    assert CONTEXT_MENU_THEME_MARKER in (view_menu.styleSheet() or "")

    submenu_actions = [action for action in view_menu.actions() if action.menu() is not None]
    submenu_labels = [action.text().lower() for action in submenu_actions]
    assert any(label.startswith("x ") and "axis" in label for label in submenu_labels)
    assert any(label.startswith("y ") and "axis" in label for label in submenu_labels)
    assert any("mouse mode" in label for label in submenu_labels)

    for action in submenu_actions:
        assert CONTEXT_MENU_THEME_MARKER in (action.menu().styleSheet() or "")

    plot_widget.close()


def test_global_styler_styles_plain_qmenu_and_dynamic_submenu(app):
    apply_global_stylesheet(app)

    root_menu = QMenu("Root Menu")
    root_menu.addAction("Initial")
    root_menu.show()
    app.processEvents()

    assert CONTEXT_MENU_THEME_MARKER in (root_menu.styleSheet() or "")

    dynamic_submenu = root_menu.addMenu("Dynamic Submenu")
    dynamic_submenu.addAction("Nested Action")
    root_menu.show()
    app.processEvents()

    assert CONTEXT_MENU_THEME_MARKER in (dynamic_submenu.styleSheet() or "")

    root_menu.close()


def test_plotwidget_parent_injected_submenus_get_themed(app):
    plot_widget = pg.PlotWidget()
    apply_context_menu_style(plot_widget)
    app.processEvents()

    plot_item = plot_widget.getPlotItem()
    view_box = plot_item.getViewBox()
    view_menu = view_box.menu
    scene = plot_widget.scene()

    scene.addParentContextMenus(
        view_box,
        view_menu,
        SimpleNamespace(acceptedItem=view_box),
    )
    view_menu.aboutToShow.emit()
    app.processEvents()

    plot_options_action = next(
        (
            action
            for action in view_menu.actions()
            if action.menu() is not None and "plot" in action.text().lower()
        ),
        None,
    )
    assert plot_options_action is not None
    assert CONTEXT_MENU_THEME_MARKER in (plot_options_action.menu().styleSheet() or "")

    plot_widget.close()


def test_pyqtgraph_export_dialog_gets_global_tool_theme(app):
    apply_global_stylesheet(app)
    plot_widget = pg.PlotWidget()
    scene = plot_widget.scene()
    dialog = ExportDialog(scene)
    dialog.show()
    app.processEvents()

    assert dialog.objectName() == PYQTGRAPH_EXPORT_DIALOG_OBJECT_NAME
    stylesheet = dialog.styleSheet() or ""
    assert PYQTGRAPH_TOOL_THEME_MARKER in stylesheet
    assert "QTreeWidget::item:selected" in stylesheet
    assert "QListWidget" in stylesheet
    assert "QPushButton" in stylesheet
    assert hasattr(dialog, "_spectral_edge_export_base_height")
    assert hasattr(dialog, "_spectral_edge_export_target_height")
    assert dialog._spectral_edge_export_target_height == math.ceil(dialog._spectral_edge_export_base_height * 1.25)
    assert dialog.minimumHeight() >= dialog._spectral_edge_export_target_height

    current_item = dialog.ui.formatList.currentItem()
    assert current_item is not None
    assert "image file" in current_item.text().lower()

    dialog.close()
    plot_widget.close()


def test_deleted_qmenu_is_ignored_by_styler(app):
    menu = QMenu("Transient")
    menu.deleteLater()
    app.processEvents()

    # Should not raise even if the wrapped C++ menu object is gone.
    _apply_menu_tree_style(menu)
