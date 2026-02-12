import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from spectral_edge.gui.event_manager import Event, EventManagerWindow


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_event_manager_preserves_enabled_state_on_table_refresh(app):
    manager = EventManagerWindow(max_time=20.0, min_time=0.0)
    manager.events = [
        Event("Event A", 1.0, 2.0),
        Event("Event B", 3.0, 4.0),
        Event("Event C", 5.0, 6.0),
    ]
    manager._update_table()

    manager.table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
    manager._update_table()

    assert manager.table.item(0, 0).checkState() == Qt.CheckState.Checked
    assert manager.table.item(1, 0).checkState() == Qt.CheckState.Unchecked
    assert manager.table.item(2, 0).checkState() == Qt.CheckState.Checked
    manager.close()


def test_event_manager_get_enabled_events_reads_checkbox_state(app):
    manager = EventManagerWindow(max_time=20.0, min_time=0.0)
    manager.events = [
        Event("Event A", 1.0, 2.0),
        Event("Event B", 3.0, 4.0),
    ]
    manager._update_table()

    manager.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    enabled = manager.get_enabled_events()

    assert len(enabled) == 1
    assert enabled[0].name == "Event B"
    manager.close()
