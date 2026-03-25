"""Qt main window tests (Windows only; PySide6 is not exercised on Linux CI)."""

from __future__ import annotations

import os
import sys

import pytest

if sys.platform != 'win32':
    pytest.skip(
        'Windows only: Qt widget tests require a Windows display stack.',
        allow_module_level=True,
    )

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from aetherflow.core.entitlements import RoleName
from aetherflow.main import build_main_window, build_shell
from aetherflow.ui.window import AetherflowMainWindow


def _app() -> QApplication:
    """Return a QApplication instance for widget tests."""

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_renders_shell_state_and_notices(monkeypatch, tmp_path) -> None:
    """Render the shell into a real main window."""

    _app()
    verification_dir = tmp_path / 'logs' / 'verification'
    verification_dir.mkdir(parents=True)
    (verification_dir / 'pending_app_checks.json').write_text(
        (
            '{"pending": [{"item_id": "AF-03-01", "message": "New feature added, '
            'check for functionality", "app_surface": "capture-panel"}]}\n'
        ),
        encoding='utf-8',
    )
    (verification_dir / 'status_snapshot.json').write_text(
        '{"items": {"AF-03-01": "verified"}}\n',
        encoding='utf-8',
    )
    monkeypatch.chdir(tmp_path)

    shell = build_shell()
    window = build_main_window(shell)

    assert isinstance(window, AetherflowMainWindow)
    assert window.windowTitle() == 'Aetherflow'
    assert window.route_list.count() == 4
    assert window.panel_title_label.text() == 'Home'
    assert window.panel_body_label.text()
    assert window.runtime_state_value.text() == 'RUNNING'
    assert window.notices_list.count() == 1
    assert 'check for functionality' in window.notices_list.item(0).text().lower()


def test_main_window_filters_visible_routes_by_role() -> None:
    """Render the full route list for an admin-capable session."""

    _app()
    shell = build_shell(role=RoleName.ADMIN_OPERATOR)
    window = build_main_window(shell, role=RoleName.ADMIN_OPERATOR)

    visible_routes = [
        window.route_list.item(index).data(Qt.ItemDataRole.UserRole)
        for index in range(window.route_list.count())
    ]

    assert visible_routes == [
        'home',
        'catalog',
        'capture',
        'workers',
        'environment',
        'resources',
        'admin',
    ]


def test_main_window_navigation_updates_active_panel() -> None:
    """Update the rendered panel when the user selects a route."""

    _app()
    shell = build_shell()
    window = build_main_window(shell)

    window.navigate_to('capture')

    assert shell.active_panel_id() == 'panel.capture'
    assert window.panel_title_label.text() == 'Capture'
    assert 'capture' in window.panel_body_label.text().lower()


def test_main_window_renders_catalog_panel_entries() -> None:
    """Render a real catalog panel with plugin rows and summary counts."""

    _app()
    shell = build_shell()
    window = build_main_window(shell)

    window.navigate_to('catalog')

    assert window.catalog_panel is not None
    assert window.panel_stack.currentWidget() is window.catalog_panel
    assert window.catalog_panel.summary_label.text() == '2 available, 1 locked, 0 grace'
    assert window.catalog_panel.entry_list.count() == 3
    assert 'XInput Provider' in window.catalog_panel.entry_list.item(0).text()
    assert 'Keyboard & Mouse' in window.catalog_panel.entry_list.item(1).text()
    assert 'MF Capture' in window.catalog_panel.entry_list.item(2).text()
    assert 'LOCKED' in window.catalog_panel.entry_list.item(2).text()
