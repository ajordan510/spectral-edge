from spectral_edge.gui.parameter_tooltips import get_tooltip


def test_frequency_resolution_tooltip_uses_5hz_aerospace_standard():
    tooltip = get_tooltip("frequency_resolution")
    assert "5.0 Hz" in tooltip
    assert "1.0 Hz (per SMC-S-016)" not in tooltip
    assert "&Delta;" in tooltip
    assert "&rarr;" in tooltip
    assert "\u00ce" not in tooltip
    assert "\u00e2" not in tooltip
