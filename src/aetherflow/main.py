"""Application entrypoints for Aetherflow."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from aetherflow.core.developer_app_checks import PendingAppCheckStore
from aetherflow.core.dotenv_bootstrap import configure_environment
from aetherflow.core.entitlements import RoleName
from aetherflow.ui.bootstrap import configure_default_shell
from aetherflow.ui.shell import ShellModel


def build_shell(*, role: RoleName = RoleName.POWER_GAMER) -> ShellModel:
    """Build the shell model, load notices, and configure startup UI.

    Args:
        role: Active role used to configure the default startup shell.

    Returns:
        Shell model ready for startup.

    """
    shell = ShellModel()
    store = PendingAppCheckStore(
        pending_path=Path('logs') / 'verification' / 'pending_app_checks.json',
        snapshot_path=Path('logs') / 'verification' / 'status_snapshot.json',
    )

    pending_alerts = store.pending_alerts()
    shell.load_pending_app_checks(pending_alerts)
    for alert in pending_alerts:
        store.acknowledge(alert.item_id)

    return configure_default_shell(shell, role=role)


def main() -> int:
    """Run the minimal Aetherflow shell entrypoint.

    Returns:
        Process exit code.

    """
    configure_environment()
    shell = build_shell()
    logger.info('Starting Aetherflow shell bootstrap.')
    logger.debug('Startup notices loaded: {}', len(shell.notices))
    return 0
