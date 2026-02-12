from spectral_edge.gui.global_styles import get_combined_stylesheet
from spectral_edge.utils.theme import (
    CONTEXT_MENU_THEME_MARKER,
    PYQTGRAPH_EXPORT_DIALOG_OBJECT_NAME,
    PYQTGRAPH_TOOL_THEME_MARKER,
)


def test_combined_stylesheet_includes_readable_tooltips():
    stylesheet = get_combined_stylesheet()
    assert "QToolTip" in stylesheet
    assert "color: #ffffff" in stylesheet


def test_combined_stylesheet_includes_context_menu_theme_rules():
    stylesheet = get_combined_stylesheet()
    assert CONTEXT_MENU_THEME_MARKER in stylesheet
    assert "QMenu::item:selected" in stylesheet
    assert "QMenu::item:disabled" in stylesheet
    assert "QMenu::separator" in stylesheet
    assert "QMenu::indicator:non-exclusive:checked" in stylesheet
    assert "QMenu::indicator:exclusive:checked" in stylesheet
    assert "QMenu::right-arrow" in stylesheet
    assert "QMenu QSlider::handle:horizontal" in stylesheet
    assert PYQTGRAPH_TOOL_THEME_MARKER in stylesheet
    assert f"QWidget#{PYQTGRAPH_EXPORT_DIALOG_OBJECT_NAME}" in stylesheet
    assert "QTreeWidget::item:selected" in stylesheet
