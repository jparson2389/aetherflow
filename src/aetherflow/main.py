"""Application entrypoints for Aetherflow."""

from pathlib import Path

from loguru import logger

from aetherflow.core.developer_app_checks import PendingAppCheckStore
from aetherflow.core.dotenv_bootstrap import configure_environment
from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.runtime_state import RuntimeState
from aetherflow.ui.router import RouteDefinition
from aetherflow.ui.shell import ShellModel
from aetherflow.ui.status_hud import StatusHUDModel


def build_shell() -> ShellModel:
    """Build the shell model and load pending developer app checks.

    Returns:
        Shell model ready for startup.

    """
    shell = ShellModel()

    # Register default routes
    shell.router.register_route(
        RouteDefinition(name='catalog', title='Plugin Catalog', panel_id='panel.catalog')
    )
    shell.router.register_route(
        RouteDefinition(name='environment', title='Environment Manager', panel_id='panel.environment')
    )
    shell.set_active_route('catalog', role=None)

    # Initialize dummy status HUD
    shell.set_status_hud(
        StatusHUDModel(
            input_plugin='xinput',
            output_plugin='vigem',
            capture_plugin='opencv',
            display_plugin='cpu',
            measured_fps=60.0,
            jitter_ms=1.2,
            worker_health=RuntimeState.RUNNING,
            entitlement_state=EntitlementState.LOADED,
            runtime_state=RuntimeState.RUNNING,
        )
    )

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
    """Run the minimal Aetherflow shell entrypoint.

    Returns:
        Process exit code.

    """
    configure_environment()
    shell = build_shell()
    logger.info('Starting Aetherflow shell bootstrap.')
    logger.debug('Startup notices loaded: {}', len(shell.notices))

    # If we are in a GUI context, launch the main window
    import sys
    if 'aetherflow-gui' in sys.argv[0] or '--gui' in sys.argv:
        from aetherflow.ui.main_window import run_app
        return run_app(shell)

    return 0
