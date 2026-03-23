"""Application entrypoints for Aetherflow."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

from aetherflow.core.developer_app_checks import PendingAppCheckStore
from aetherflow.core.dotenv_bootstrap import configure_environment
from aetherflow.ui.shell import ShellModel


def build_shell() -> ShellModel:
    """Build the shell model and load pending developer app checks.

    Returns:
        Shell model ready for startup.

    """
    shell = ShellModel()
    store = PendingAppCheckStore(
        pending_path=Path('logs') / 'verification' / 'pending_app_checks.json',
        snapshot_path=Path('logs') / 'verification' / 'status_snapshot.json',
    )

    # Load pending alerts and acknowledge each so they don't reappear next startup
    pending_alerts = store.pending_alerts()
    shell.load_pending_app_checks(pending_alerts)
    for alert in pending_alerts:
        store.acknowledge(alert.item_id)

    return shell


def main() -> int:
    """Run the Aetherflow application.

    In normal mode, starts the Qt event loop and blocks until the window is
    closed.  When ``AETHERFLOW_HEADLESS=1`` is set (used by tests and CI),
    the window is created and immediately closed without entering the event
    loop.

    Returns:
        Process exit code.

    """
    configure_environment()
    shell = build_shell()
    logger.info('Starting Aetherflow.')
    logger.debug('Startup notices loaded: {}', len(shell.notices))

    headless = os.environ.get('AETHERFLOW_HEADLESS', '').strip() == '1'
    if headless:
        logger.debug('Headless mode: skipping Qt startup.')
        return 0

    from PySide6.QtWidgets import QApplication

    from aetherflow.ui.app_window import AppWindow

    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = AppWindow(shell)
    window.show()
    return app.exec()
