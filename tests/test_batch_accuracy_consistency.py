import os
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")
from PyQt6.QtWidgets import QApplication, QFileDialog

from spectral_edge.batch.config import BatchConfig, EventDefinition, OutputConfig, PSDConfig
from spectral_edge.batch.csv_output import _create_event_csv
from spectral_edge.batch.output_psd import apply_frequency_spacing
from spectral_edge.batch.powerpoint_output import (
    _add_rms_summary_slides,
    _build_plot_parameter_boxes,
    _get_event_definitions,
)
from spectral_edge.batch.processor import BatchProcessor
from spectral_edge.gui.batch_processor_window import BatchProcessorWindow


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_output_config_defaults_excel_and_powerpoint_only():
    config = OutputConfig()
    assert config.excel_enabled is True
    assert config.powerpoint_enabled is True
    assert config.csv_enabled is False
    assert config.hdf5_writeback_enabled is False


def test_include_full_duration_respects_checkbox_only():
    cfg = BatchConfig(
        source_type="csv",
        source_files=["dummy.csv"],
        process_full_duration=False,
        events=[EventDefinition(name="start", start_time=0.0, end_time=1.0)],
    )
    processor = BatchProcessor(cfg)
    assert processor._include_full_duration() is False

    cfg.process_full_duration = True
    assert processor._include_full_duration() is True


def test_get_event_definitions_does_not_force_full_duration():
    cfg = BatchConfig(
        process_full_duration=False,
        events=[EventDefinition(name="mid", start_time=1.0, end_time=2.0)],
    )
    assert _get_event_definitions(cfg) == [("mid", 1.0, 2.0)]

    cfg.process_full_duration = True
    assert _get_event_definitions(cfg)[0] == ("full_duration", None, None)


def test_maximax_respects_requested_df_when_efficient_fft_disabled():
    sample_rate = 10_000.0
    t = np.arange(0.0, 10.0, 1.0 / sample_rate)
    signal = np.sin(2.0 * np.pi * 123.0 * t)
    cfg = BatchConfig(
        source_type="csv",
        source_files=["dummy.csv"],
        psd_config=PSDConfig(
            method="maximax",
            desired_df=5.0,
            use_efficient_fft=False,
            overlap_percent=50.0,
        ),
    )
    processor = BatchProcessor(cfg)
    freqs, _psd = processor._calculate_psd(signal, sample_rate)
    assert len(freqs) > 2
    assert (freqs[1] - freqs[0]) == pytest.approx(5.0, rel=1e-6, abs=1e-9)


def test_process_event_metadata_has_requested_and_actual_df_and_no_mean_removal():
    sample_rate = 1000.0
    t = np.arange(0.0, 4.0, 1.0 / sample_rate)
    signal = np.sin(2.0 * np.pi * 30.0 * t)
    cfg = BatchConfig(
        source_type="csv",
        source_files=["dummy.csv"],
        process_full_duration=False,
        psd_config=PSDConfig(method="welch", desired_df=5.0, use_efficient_fft=False),
    )
    processor = BatchProcessor(cfg)
    processor._process_event(
        "flight_1",
        "chan_1",
        "event_1",
        t,
        signal,
        sample_rate,
        "g",
        start_time=0.0,
        end_time=2.0,
    )
    metadata = processor.result.channel_results[("flight_1", "chan_1")]["event_1"]["metadata"]
    assert metadata["mean_removed"] is False
    assert metadata["requested_df_hz"] == pytest.approx(5.0)
    assert metadata["actual_df_hz"] == pytest.approx(5.0, rel=1e-6, abs=1e-9)


def test_apply_frequency_spacing_clips_constant_bandwidth_range():
    cfg = BatchConfig()
    cfg.psd_config.frequency_spacing = "constant_bandwidth"
    cfg.psd_config.freq_min = 20.0
    cfg.psd_config.freq_max = 2000.0
    frequencies = np.array([0.0, 10.0, 20.0, 100.0, 2000.0, 2500.0])
    psd = np.arange(frequencies.size, dtype=float)
    clipped_freqs, clipped_psd = apply_frequency_spacing(frequencies, psd, cfg.psd_config)
    assert np.all(clipped_freqs >= 20.0)
    assert np.all(clipped_freqs <= 2000.0)
    assert clipped_freqs.tolist() == [20.0, 100.0, 2000.0]
    assert clipped_psd.tolist() == [2.0, 3.0, 4.0]


def test_create_event_csv_uses_outer_frequency_alignment_and_prefix(tmp_path):
    event_results = {
        "chan_a": {
            "frequencies": np.array([20.0, 40.0, 60.0], dtype=float),
            "psd": np.array([1.0, 2.0, 3.0], dtype=float),
            "metadata": {},
        },
        "chan_b": {
            "frequencies": np.array([40.0, 80.0], dtype=float),
            "psd": np.array([4.0, 5.0], dtype=float),
            "metadata": {},
        },
    }
    path = _create_event_csv(tmp_path, "start", event_results, filename_prefix="demo_prefix")
    assert path is not None
    assert os.path.basename(path) == "demo_prefix_start_psd.csv"

    exported = pd.read_csv(path)
    assert exported["Frequency_Hz"].tolist() == [20.0, 40.0, 60.0, 80.0]
    assert np.isnan(exported.loc[0, "chan_b"])
    assert np.isnan(exported.loc[2, "chan_b"])
    assert np.isnan(exported.loc[3, "chan_a"])


def test_build_plot_parameter_boxes_never_reports_filter_none():
    cfg = BatchConfig()
    left, right = _build_plot_parameter_boxes(
        cfg,
        event_name="start",
        start_time=0.0,
        end_time=1.0,
        sample_rate=1000.0,
        units="g",
        event_result={"metadata": {"applied_highpass_hz": 1.0, "applied_lowpass_hz": 450.0}},
    )
    assert "Filter=None" not in left
    assert "Filter=Baseline" in left or "Filter=Baseline+user" in left
    assert "SNR=" in right


def test_rms_summary_slides_paginate_and_include_units():
    class StubReportGenerator:
        def __init__(self):
            self.calls = []

        def add_rms_table_slide(self, title, headers, rows):
            self.calls.append((title, headers, rows))

    channel_results = {}
    for channel_idx in range(5):
        event_dict = {}
        for event_idx in range(5):
            event_dict[f"event_{event_idx}"] = {
                "metadata": {"rms": float(channel_idx + event_idx + 0.5), "units": "g"}
            }
        channel_results[(f"flight_{channel_idx}", f"chan_{channel_idx}")] = event_dict

    results = SimpleNamespace(channel_results=channel_results)
    config = BatchConfig()
    config.powerpoint_config.include_3sigma_columns = True
    report = StubReportGenerator()
    _add_rms_summary_slides(report, results, config)

    assert len(report.calls) == 2
    for title, headers, rows in report.calls:
        assert "Units" in headers
        assert len(rows) <= 20
        assert title.startswith("RMS Summary")


def test_hdf5_selection_auto_launches_channel_navigator(app, monkeypatch, tmp_path):
    fake_file = tmp_path / "demo.h5"
    fake_file.write_text("placeholder", encoding="utf-8")

    window = BatchProcessorWindow()
    calls = {"channel_dialog_opened": 0}

    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        staticmethod(lambda *args, **kwargs: ([str(fake_file)], "HDF5 Files (*.h5 *.hdf5)")),
    )
    monkeypatch.setattr(window, "_on_select_channels", lambda: calls.__setitem__("channel_dialog_opened", 1))

    window.selected_channels = [("old", "channel")]
    window.config.selected_channels = [("old", "channel")]
    window.channels_text.setText("old/channel")

    window._on_select_hdf5()

    assert window.config.source_type == "hdf5"
    assert window.config.source_files == [str(fake_file)]
    assert window.selected_channels == []
    assert window.config.selected_channels == []
    assert window.channels_text.toPlainText() == ""
    assert calls["channel_dialog_opened"] == 1
    window.close()


def test_output_tab_defaults_to_excel_and_powerpoint_and_prefix_field_exists(app):
    window = BatchProcessorWindow()
    assert window.excel_checkbox.isChecked() is True
    assert window.powerpoint_checkbox.isChecked() is True
    assert window.csv_checkbox.isChecked() is False
    assert window.hdf5_checkbox.isChecked() is False
    assert hasattr(window, "output_prefix_edit")
    window.close()
