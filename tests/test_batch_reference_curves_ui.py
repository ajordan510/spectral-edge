import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QGridLayout

from spectral_edge.gui.batch_processor_window import BatchProcessorWindow
from spectral_edge.batch.config import ReferenceCurveConfig


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_batch_reference_curve_controls_exist_and_builtin_toggle(app):
    window = BatchProcessorWindow()
    window.show()
    app.processEvents()

    assert hasattr(window, "batch_minimum_screening_checkbox")
    assert hasattr(window, "batch_minimum_screening_plus_3db_checkbox")
    assert window.batch_minimum_screening_checkbox.isChecked() is False
    assert window.batch_minimum_screening_plus_3db_checkbox.isChecked() is False

    window.batch_minimum_screening_checkbox.setChecked(True)
    app.processEvents()
    assert any(
        curve.get("source") == "builtin" and curve.get("builtin_id") == "minimum_screening"
        for curve in window.batch_reference_curves
    )

    window.close()


def test_batch_reference_curve_import_like_add_remove_and_config_sync(app):
    window = BatchProcessorWindow()
    window.show()
    app.processEvents()

    window._add_batch_reference_curve(
        {
            "name": "Imported Curve",
            "frequencies": [25.0, 100.0, 1000.0, 1900.0],
            "psd": [0.02, 0.06, 0.06, 0.02],
            "enabled": True,
            "source": "imported",
            "file_path": "imported.csv",
            "color": "#4d96ff",
            "line_style": "dashed",
        }
    )
    assert any(curve.get("name") == "Imported Curve" for curve in window.batch_reference_curves)

    imported_index = next(
        idx for idx, curve in enumerate(window.batch_reference_curves)
        if curve.get("name") == "Imported Curve"
    )
    window._remove_batch_reference_curve(imported_index)
    assert not any(curve.get("name") == "Imported Curve" for curve in window.batch_reference_curves)

    window.batch_minimum_screening_checkbox.setChecked(True)
    window._update_config_from_ui()
    stored_curves = window.config.powerpoint_config.reference_curves
    assert any(
        isinstance(curve, ReferenceCurveConfig) and curve.builtin_id == "minimum_screening"
        for curve in stored_curves
    )

    window.close()


def test_batch_reference_curve_list_uses_four_column_grid(app):
    window = BatchProcessorWindow()
    window.show()
    app.processEvents()

    assert isinstance(window.batch_reference_curve_list_layout, QGridLayout)
    assert window.batch_reference_curve_columns == 4

    for idx in range(5):
        window._add_batch_reference_curve(
            {
                "name": f"Curve {idx + 1}",
                "frequencies": [20.0, 80.0, 800.0, 2000.0],
                "psd": [0.01, 0.04, 0.04, 0.01],
                "enabled": True,
                "source": "imported",
                "file_path": f"curve_{idx + 1}.csv",
                "color": "#4d96ff",
                "line_style": "dashed",
            }
        )

    layout = window.batch_reference_curve_list_layout
    assert layout.itemAtPosition(0, 0) is not None
    assert layout.itemAtPosition(0, 3) is not None
    assert layout.itemAtPosition(1, 0) is not None

    window.close()
