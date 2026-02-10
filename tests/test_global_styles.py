from spectral_edge.gui.global_styles import get_combined_stylesheet


def test_combined_stylesheet_includes_readable_tooltips():
    stylesheet = get_combined_stylesheet()
    assert "QToolTip" in stylesheet
    assert "color: #ffffff" in stylesheet
