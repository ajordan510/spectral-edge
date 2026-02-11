import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QVBoxLayout, QCheckBox

from spectral_edge.gui.psd_window import PSDAnalysisWindow
from spectral_edge.utils.reference_curves import sanitize_reference_curve


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_psd_builtin_reference_curves_toggle_and_dedupe(app):
    window = PSDAnalysisWindow()
    window.show()
    app.processEvents()

    assert window.minimum_screening_checkbox is not None
    assert window.minimum_screening_plus_3db_checkbox is not None

    window.minimum_screening_checkbox.setChecked(True)
    app.processEvents()
    assert isinstance(window.quick_curves_layout, QVBoxLayout)
    assert window.comparison_scroll.minimumHeight() >= 170

    builtin_curves = [
        curve for curve in window.comparison_curves
        if curve.get("source") == "builtin" and curve.get("builtin_id") == "minimum_screening"
    ]
    assert len(builtin_curves) == 1
    assert list(builtin_curves[0]["frequencies"]) == [20.0, 80.0, 800.0, 2000.0]
    assert list(builtin_curves[0]["psd"]) == [0.01, 0.04, 0.04, 0.01]

    window.comparison_curves.append(window._build_builtin_comparison_curve_data("minimum_screening"))
    window._sync_builtin_reference_curves()
    builtin_curves_after = [
        curve for curve in window.comparison_curves
        if curve.get("source") == "builtin" and curve.get("builtin_id") == "minimum_screening"
    ]
    assert len(builtin_curves_after) == 1
    window._update_comparison_list()
    comparison_checkboxes = window.comparison_list_widget.findChildren(QCheckBox)
    assert comparison_checkboxes
    assert "RMS=" in comparison_checkboxes[0].text()
    assert "gRMS" not in comparison_checkboxes[0].text()

    window.close()


def test_psd_reference_curve_plotting_not_trimmed_by_psd_freq_range(app):
    window = PSDAnalysisWindow()
    window.show()
    app.processEvents()

    normalized_curve = sanitize_reference_curve(
        name="Wide Curve",
        frequencies=[10.0, 20.0, 800.0, 2000.0, 2500.0],
        psd=[0.01, 0.02, 0.04, 0.02, 0.01],
        source="imported",
        enabled=True,
        color="#ff6b6b",
        line_style="dashed",
        file_path="wide.csv",
    )
    window.comparison_curves = [window._curve_dict_from_normalized(normalized_curve)]
    window.channel_names = ["Ch1"]
    window.channel_units = ["g"]
    window.channel_flight_names = [""]
    window.channel_checkboxes = [QCheckBox()]
    window.channel_checkboxes[0].setChecked(True)
    window.frequencies = {"Ch1": np.array([20.0, 40.0, 80.0, 160.0, 320.0, 640.0, 1280.0, 2000.0])}
    window.psd_results = {"Ch1": np.array([0.02, 0.03, 0.05, 0.06, 0.05, 0.04, 0.03, 0.02])}
    window.rms_values = {"Ch1": 0.25}
    window.freq_min_spin.setValue(20.0)
    window.freq_max_spin.setValue(2000.0)

    captured_reference_x = []
    original_plot = window.plot_widget.plot

    def _capture_plot(*args, **kwargs):
        name = kwargs.get("name", "")
        if isinstance(name, str) and name.startswith("Ref:"):
            captured_reference_x.append(np.asarray(args[0], dtype=np.float64))
        return original_plot(*args, **kwargs)

    window.plot_widget.plot = _capture_plot
    window._update_plot()
    app.processEvents()

    assert captured_reference_x
    reference_x = captured_reference_x[-1]
    assert np.min(reference_x) <= 10.0
    assert np.max(reference_x) >= 2500.0

    window.close()


def test_psd_imported_reference_curve_remove_and_clear_resets_builtins(app):
    window = PSDAnalysisWindow()
    window.show()
    app.processEvents()

    window.minimum_screening_checkbox.setChecked(True)
    window.minimum_screening_plus_3db_checkbox.setChecked(True)
    app.processEvents()

    imported_curve = sanitize_reference_curve(
        name="Imported Curve",
        frequencies=[30.0, 120.0, 800.0, 1500.0],
        psd=[0.02, 0.06, 0.06, 0.02],
        source="imported",
        enabled=True,
        color="#ff6b6b",
        line_style="dashed",
        file_path="dummy.csv",
    )
    window.comparison_curves.append(window._curve_dict_from_normalized(imported_curve))
    window._update_comparison_list()

    imported_index = next(
        idx for idx, curve in enumerate(window.comparison_curves)
        if curve.get("source") == "imported" and curve.get("name") == "Imported Curve"
    )
    window._remove_comparison_curve(imported_index)
    assert not any(
        curve.get("source") == "imported" and curve.get("name") == "Imported Curve"
        for curve in window.comparison_curves
    )

    window._clear_comparison_curves()
    assert window.minimum_screening_checkbox.isChecked() is False
    assert window.minimum_screening_plus_3db_checkbox.isChecked() is False
    assert len(window.comparison_curves) == 0

    window.close()
