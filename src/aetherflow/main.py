"""Application entrypoints for Aetherflow."""

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
    shell.load_pending_app_checks(store.pending_alerts())
    return shell


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
