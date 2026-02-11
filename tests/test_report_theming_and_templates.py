import io
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")
from PyQt6.QtWidgets import QApplication, QWidget

from spectral_edge.gui.psd_window import PSDReportOptionsDialog
from spectral_edge.gui import statistics_window as statistics_module
from spectral_edge.utils.report_generator import ReportGenerator, PPTX_AVAILABLE


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def _build_png_bytes():
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(2.0, 1.4))
    ax.plot([0.0, 1.0], [0.0, 1.0])
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return buf.getvalue()


def test_psd_report_options_dialog_uses_scoped_dark_theme(app):
    parent = QWidget()
    parent.setStyleSheet("QDialog { background-color: #ffffff; color: #000000; }")

    dialog = PSDReportOptionsDialog(parent)
    dialog.show()
    app.processEvents()

    stylesheet = dialog.styleSheet()
    assert dialog.objectName() == "psdReportOptionsDialog"
    assert "QDialog#psdReportOptionsDialog" in stylesheet
    assert "#1a1f2e" in stylesheet

    dialog.close()
    parent.close()


def test_statistics_report_path_uses_canonical_template_methods(monkeypatch, app, tmp_path):
    captured = {"calls": []}

    class FakeReportGenerator:
        def __init__(self, *args, **kwargs):
            captured["kwargs"] = kwargs

        def add_title_slide(self, *args, **kwargs):
            captured["calls"].append("add_title_slide")

        def add_bulleted_sections_slide(self, *args, **kwargs):
            captured["calls"].append("add_bulleted_sections_slide")

        def add_single_plot_slide(self, *args, **kwargs):
            captured["calls"].append("add_single_plot_slide")

        def add_rms_table_slide(self, *args, **kwargs):
            captured["calls"].append("add_rms_table_slide")

        def add_psd_plot(self, *args, **kwargs):
            raise AssertionError("Legacy add_psd_plot should not be used by statistics report path")

        def add_comparison_plot(self, *args, **kwargs):
            raise AssertionError("Legacy add_comparison_plot should not be used by statistics report path")

        def add_summary_table(self, *args, **kwargs):
            raise AssertionError("Legacy add_summary_table should not be used by statistics report path")

        def save(self, output_path):
            captured["save_path"] = output_path
            return output_path

    monkeypatch.setattr(statistics_module, "PPTX_AVAILABLE", True)
    monkeypatch.setattr(statistics_module, "ReportGenerator", FakeReportGenerator)
    monkeypatch.setattr(statistics_module, "export_plot_to_image", lambda *args, **kwargs: b"fake-image")
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(tmp_path / "stats_report.pptx"), "PowerPoint Files (*.pptx)"),
    )
    monkeypatch.setattr(statistics_module, "show_information", lambda *args, **kwargs: None)
    monkeypatch.setattr(statistics_module, "show_warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(statistics_module, "show_critical", lambda *args, **kwargs: None)

    window = statistics_module.create_statistics_window(
        channels_data=[("Accel_X", [0.0, 1.0, 0.5, -0.2], "g", "flight_001")],
        sample_rate=100.0,
        processing_note="Filter: none | Running Mean Not Removed",
    )
    window.pdf_data = {
        "Accel_X": {
            "overall": {"rms": 1.2345},
            "unit": "g",
        }
    }

    window._generate_report()
    app.processEvents()

    assert captured["kwargs"]["watermark_scope"] == "plot_slides"
    assert "add_title_slide" in captured["calls"]
    assert "add_bulleted_sections_slide" in captured["calls"]
    assert captured["calls"].count("add_single_plot_slide") == 2
    assert "add_rms_table_slide" in captured["calls"]
    window.close()


@pytest.mark.skipif(not PPTX_AVAILABLE, reason="python-pptx not installed")
def test_report_generator_adds_watermark_to_plot_slides_only():
    image_bytes = _build_png_bytes()
    watermark = "pyMARVIN TEST"
    generator = ReportGenerator(
        title="Watermark Test",
        watermark_text=watermark,
        watermark_scope="plot_slides",
    )

    generator.add_single_plot_slide(image_bytes, "Plot Slide")
    generator.add_text_slide("Notes", "No plot on this slide")

    first_slide_texts = [shape.text for shape in generator.presentation.slides[0].shapes if hasattr(shape, "text")]
    second_slide_texts = [shape.text for shape in generator.presentation.slides[1].shapes if hasattr(shape, "text")]

    assert any(watermark in text for text in first_slide_texts)
    assert all(watermark not in text for text in second_slide_texts)

    watermark_shape = next(
        shape
        for shape in generator.presentation.slides[0].shapes
        if hasattr(shape, "text") and shape.text == watermark
    )
    assert watermark_shape.left > int(generator.presentation.slide_width * 0.60)
    assert watermark_shape.top < int(generator.presentation.slide_height * 0.12)


def test_no_plot_level_watermark_calls_in_batch_ppt_builders():
    target_files = [
        Path("spectral_edge/batch/powerpoint_output.py"),
        Path("spectral_edge/batch/statistics.py"),
    ]
    for file_path in target_files:
        source = file_path.read_text(encoding="utf-8")
        assert "add_watermark(" not in source


def test_active_report_paths_no_longer_call_legacy_report_generator_apis():
    legacy_calls = [
        ".add_psd_plot(",
        ".add_comparison_plot(",
        ".add_summary_table(",
    ]
    target_files = [
        Path("spectral_edge/gui/psd_window.py"),
        Path("spectral_edge/gui/statistics_window.py"),
        Path("spectral_edge/batch/powerpoint_output.py"),
    ]
    for file_path in target_files:
        source = file_path.read_text(encoding="utf-8")
        for legacy_call in legacy_calls:
            assert legacy_call not in source
