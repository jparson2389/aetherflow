"""Helpers for building a visible Aetherflow shell."""

from __future__ import annotations

from aetherflow.core.entitlements import EntitlementState, RoleName
from aetherflow.core.runtime_state import RuntimeState
from aetherflow.core.services import create_default_services
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion
from aetherflow.plugins.registry import PluginRegistry
from aetherflow.ui.panels.plugin_catalog_panel import PluginCatalogPanelModel
from aetherflow.ui.router import RouteDefinition, RouterModel
from aetherflow.ui.shell import ShellModel
from aetherflow.ui.status_hud import StatusHUDModel


def configure_default_shell(
    shell: ShellModel,
    *,
    role: RoleName = RoleName.POWER_GAMER,
) -> ShellModel:
    """Attach default routes and a visible status HUD to the shell.

    Args:
        shell: Shell model to configure.
        role: Active role for startup route visibility and catalog state.

    Returns:
        The configured shell.

    """
    if not shell.router.order:
        shell.router = _build_default_router()
    if shell.status_hud is None:
        shell.set_status_hud(_build_default_hud())
    if shell.plugin_catalog is None:
        shell.set_plugin_catalog(_build_default_catalog(role=role))
    if shell.router.active_route is None:
        shell.set_active_route('home', role=role)
    return shell


def _build_default_router() -> RouterModel:
    """Build the default shell routes for the current app slice."""
    router = RouterModel()
    for route in (
        RouteDefinition(name='home', title='Home', panel_id='panel.home'),
        RouteDefinition(name='catalog', title='Catalog', panel_id='panel.catalog'),
        RouteDefinition(name='capture', title='Capture', panel_id='panel.capture'),
        RouteDefinition(name='workers', title='Workers', panel_id='panel.workers'),
        RouteDefinition(
            name='environment',
            title='Environment',
            panel_id='panel.environment',
            allowed_roles=(
                RoleName.VISION_ML_TINKERER,
                RoleName.ADMIN_OPERATOR,
            ),
        ),
        RouteDefinition(
            name='resources',
            title='Resources',
            panel_id='panel.resources',
            allowed_roles=(
                RoleName.VISION_ML_TINKERER,
                RoleName.ADMIN_OPERATOR,
            ),
        ),
        RouteDefinition(
            name='admin',
            title='Admin',
            panel_id='panel.admin',
            allowed_roles=(RoleName.ADMIN_OPERATOR,),
        ),
    ):
        router.register_route(route)
    return router


def _build_default_hud() -> StatusHUDModel:
    """Build a startup HUD snapshot for the shell."""
    return StatusHUDModel(
        input_plugin='xinput',
        output_plugin='virtual-controller',
        capture_plugin='opencv',
        display_plugin='shell',
        measured_fps=60.0,
        jitter_ms=1.2,
        worker_health=RuntimeState.RUNNING,
        entitlement_state=EntitlementState.LOADED,
        runtime_state=RuntimeState.RUNNING,
    )


def _build_default_catalog(*, role: RoleName) -> PluginCatalogPanelModel:
    """Build a startup catalog panel for the shell."""
    services = create_default_services()
    registry = PluginRegistry(services=services)
    for manifest in (
        PluginManifest(
            plugin_id='input.xinput',
            name='XInput Provider',
            version=PluginVersion.parse('1.0.0'),
            api_version='1.0',
            plugin_type=PluginType.INPUT,
            entrypoint='input.xinput.dll',
            premium=False,
            required_entitlements=[],
            requires_worker=False,
            signed=True,
        ),
        PluginManifest(
            plugin_id='input.kbm',
            name='Keyboard & Mouse',
            version=PluginVersion.parse('1.0.0'),
            api_version='1.0',
            plugin_type=PluginType.INPUT,
            entrypoint='aetherflow.input.kbm.KeyboardMouseInputPlugin',
            premium=False,
            required_entitlements=[],
            requires_worker=False,
            signed=True,
        ),
        PluginManifest(
            plugin_id='capture.mf',
            name='MF Capture',
            version=PluginVersion.parse('1.0.0'),
            api_version='1.0',
            plugin_type=PluginType.CAPTURE,
            entrypoint='capture.mf.dll',
            premium=True,
            required_entitlements=['vision'],
            requires_worker=False,
            signed=True,
            signature_scheme='Authenticode',
            digest_algorithm='SHA-256',
            rsa_key_bits=3072,
            publisher_thumbprint='aetherflow-publisher',
            trust_root_thumbprint='aetherflow-root',
        ),
    ):
        registry.register(manifest)
    return PluginCatalogPanelModel.from_registry(
        registry,
        role=role,
    )
