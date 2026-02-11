import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

import spectral_edge.gui.flight_navigator_enhanced as navigator_module
from spectral_edge.gui.flight_navigator_enhanced import FlightNavigator


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


class _LoaderStub:
    def __init__(self):
        self._flight_keys = ["flight_a", "flight_b"]
        self._channels = {
            "flight_a": {
                "Accel_G": SimpleNamespace(
                    units="G",
                    sample_rate=1000.0,
                    location="Wing Tip",
                    sensor_id="ACC-01",
                    description="Acceleration channel",
                    range_min=-16.0,
                    range_max=16.0,
                ),
                "Press_RMS": SimpleNamespace(
                    units="psi rms",
                    sample_rate=100.0,
                    location="Cabin Bay",
                    sensor_id="P-01",
                    description="Pressure RMS",
                    range_min=None,
                    range_max=None,
                ),
                "Press_PSIA": SimpleNamespace(
                    units="PSIA",
                    sample_rate=50.0,
                    location="Nose",
                    sensor_id="P-02",
                    description="Pressure absolute",
                    range_min=None,
                    range_max=None,
                ),
            },
            "flight_b": {
                "MissingMeta": SimpleNamespace(
                    units=None,
                    sample_rate=None,
                    location=None,
                    sensor_id=None,
                    description=None,
                    range_min=None,
                    range_max=None,
                ),
            },
        }
        self._flight_info = {
            "flight_a": SimpleNamespace(flight_id="A"),
            "flight_b": SimpleNamespace(flight_id="B"),
        }

    def get_flight_keys(self):
        return list(self._flight_keys)

    def get_channel_keys(self, flight_key):
        return list(self._channels[flight_key].keys())

    def get_flight_info(self, flight_key):
        return self._flight_info[flight_key]

    def get_channel_info(self, flight_key, channel_key):
        return self._channels[flight_key][channel_key]

    def get_time_range(self, flight_key, channel_key):
        if channel_key == "MissingMeta":
            return "N/A"
        return "0.0s - 10.0s"


def _find_channel_data(window, channel_key):
    for channel_data in window.all_channels:
        if channel_data["channel_key"] == channel_key:
            return channel_data
    raise AssertionError(f"Channel not found in test data: {channel_key}")


def test_enhanced_navigator_default_columns_and_sensor_categories(app):
    window = FlightNavigator(_LoaderStub())
    window.show()
    app.processEvents()

    visible_columns = [column.name for column in window.columns if column.visible]
    assert visible_columns == [
        "name",
        "units",
        "sample_rate",
        "location",
        "time_range",
        "sensor_id",
        "flight",
    ]

    assert "Microphone" not in window.sensor_type_checks
    assert "Pressure" in window.sensor_type_checks
    assert hasattr(window, "location_filter")

    window.close()


def test_enhanced_navigator_sensor_type_inference_handles_units_variants(app):
    window = FlightNavigator(_LoaderStub())
    window.show()
    app.processEvents()

    assert _find_channel_data(window, "Accel_G")["sensor_type"] == "Accelerometer"
    assert _find_channel_data(window, "Press_RMS")["sensor_type"] == "Pressure"
    assert _find_channel_data(window, "Press_PSIA")["sensor_type"] == "Pressure"

    window.close()


def test_enhanced_navigator_location_text_filter_is_case_insensitive_contains(app):
    window = FlightNavigator(_LoaderStub())
    window.show()
    app.processEvents()

    window.location_filter.setText("cabin")
    window._on_filter_changed()
    window._apply_filters()

    filtered_names = {channel["channel_key"] for channel in window.filtered_channels}
    assert filtered_names == {"Press_RMS"}

    window.close()


def test_enhanced_navigator_missing_metadata_renders_without_failure(app):
    window = FlightNavigator(_LoaderStub())
    window.show()
    app.processEvents()

    channel_data = _find_channel_data(window, "MissingMeta")
    item = window._create_channel_item(channel_data)
    visible_columns = [column.name for column in window.columns if column.visible]
    rendered = {name: item.text(index) for index, name in enumerate(visible_columns)}

    assert rendered["units"] == "N/A"
    assert rendered["sample_rate"] == "N/A"
    assert rendered["location"] == "N/A"
    assert rendered["sensor_id"] == "N/A"
    assert rendered["time_range"] == "N/A"

    window.search_box.setText("missing")
    window._on_search_changed("missing")
    window._apply_filters()
    assert any(channel["channel_key"] == "MissingMeta" for channel in window.filtered_channels)

    window.close()


def test_enhanced_navigator_tree_default_always_expanded_and_toggle(app):
    window = FlightNavigator(_LoaderStub())
    window.show()
    app.processEvents()

    assert window.always_expanded_check.isChecked() is True
    top_level_count = window.tree.topLevelItemCount()
    assert top_level_count > 0
    assert all(window.tree.topLevelItem(i).isExpanded() for i in range(top_level_count))

    window.always_expanded_check.setChecked(False)
    app.processEvents()
    assert all(not window.tree.topLevelItem(i).isExpanded() for i in range(top_level_count))

    window.close()


def test_enhanced_navigator_header_style_is_deterministic_against_parent_styles(app):
    class _Parent:
        def styleSheet(self):
            return "QHeaderView::section { background: #ffffff; color: #000000; }"

    window = FlightNavigator(_LoaderStub(), parent=None)
    window.setStyleSheet(window.styleSheet() + _Parent().styleSheet())
    window.show()
    app.processEvents()

    header_style = window.tree.header().styleSheet()
    assert "#1a1f2e" in header_style
    assert "#60a5fa" in header_style

    window.close()


def test_enhanced_navigator_selection_limit_blocks_accept(monkeypatch, app):
    window = FlightNavigator(
        _LoaderStub(),
        max_selected_channels=1,
        selection_limit_message="Only one channel allowed",
    )
    window.show()
    app.processEvents()

    warnings = []
    monkeypatch.setattr(
        navigator_module,
        "show_warning",
        lambda *_args: warnings.append(True),
    )

    window.selected_items = [
        ("flight_a", "Accel_G", SimpleNamespace()),
        ("flight_a", "Press_RMS", SimpleNamespace()),
    ]
    emitted = []
    window.data_selected.connect(lambda items: emitted.append(items))

    window._on_load_clicked()

    assert warnings
    assert emitted == []
    assert window.result() == 0

    window.close()
