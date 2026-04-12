from aetherflow.core.entitlements import EntitlementState, RoleName
from aetherflow.core.runtime_state import RuntimeState
from aetherflow.core.services import create_default_services
from aetherflow.plugins.catalog import CatalogLockState
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion
from aetherflow.plugins.registry import PluginRegistry
from aetherflow.ui.router import RouteDefinition, RouterModel
from aetherflow.ui.shell import ShellModel
from aetherflow.ui.status_hud import StatusHUDModel


def test_locked_premium_plugin_never_becomes_selectable() -> None:
    services = create_default_services()
    registry = PluginRegistry(services=services)
    manifest = PluginManifest(
        plugin_id='capture.mf',
        name='MF Capture',
        version=PluginVersion.parse('1.0.0'),
        api_version='1.0',
        plugin_type=PluginType.CAPTURE,
        entrypoint='capture.mf.dll',
        signed=True,
        premium=True,
        required_entitlements=['vision'],
        requires_worker=False,
        signature_scheme='Authenticode',
        digest_algorithm='SHA-256',
        rsa_key_bits=3072,
        publisher_thumbprint='aetherflow-publisher',
        trust_root_thumbprint='aetherflow-root',
    )

    registry.register(manifest)
    item = registry.catalog()[0]

    assert item.lock_state is CatalogLockState.LOCKED
    assert item.selectable is False
    assert item.purchase_cta == 'Upgrade to unlock'
    assert item.lock_reason == 'locked-premium-plugin'
    assert item.entitlement_state.value == 'LOCKED'
    assert item.premium is True
    assert item.required_entitlements == ('vision',)
    assert item.plugin_type is PluginType.CAPTURE


def test_grace_expiry_unloads_only_affected_surface_and_keeps_shell_alive() -> None:
    router = RouterModel()
    router.register_route(
        RouteDefinition(
            name='capture',
            title='Capture',
            panel_id='panel.capture',
            allowed_roles=(RoleName.POWER_GAMER,),
        )
    )
    router.register_route(
        RouteDefinition(
            name='workers',
            title='Workers',
            panel_id='panel.workers',
            allowed_roles=(RoleName.POWER_GAMER,),
        )
    )
    shell = ShellModel(
        router=router,
        active_panels=['panel.capture', 'panel.workers'],
        status_hud=StatusHUDModel(
            input_plugin='xinput',
            output_plugin='vigem',
            capture_plugin='capture.mf',
            display_plugin='render.cpu',
            measured_fps=120.0,
            jitter_ms=1.4,
            worker_health=RuntimeState.RUNNING,
            entitlement_state=EntitlementState.GRACE,
            runtime_state=RuntimeState.RUNNING,
        ),
    )
    shell.set_active_route('capture', role=RoleName.POWER_GAMER)

    shell.handle_grace_expiry('capture.mf', route_name='capture')

    assert shell.runtime_state is RuntimeState.DEGRADED
    assert shell.status_hud is not None
    assert shell.status_hud.entitlement_state is EntitlementState.LOCKED
    assert shell.status_hud.runtime_state is RuntimeState.DEGRADED
    assert shell.status_hud.show_expiry_modal is True
    assert shell.active_panel_id() is None
    assert 'panel.capture' not in shell.active_panels
    assert 'panel.workers' in shell.active_panels
    assert shell.notices[-1].message == 'Grace expired: capture.mf'

    try:
        shell.set_active_route('capture', role=RoleName.POWER_GAMER)
    except PermissionError as exc:
        assert 'grace-expired' in str(exc)
    else:
        raise AssertionError('Expected grace-expired route to be locked.')


def test_shell_survives_plugin_mark_failed() -> None:
    router = RouterModel()
    router.register_route(
        RouteDefinition(
            name='capture',
            title='Capture',
            panel_id='panel.capture',
            allowed_roles=(RoleName.POWER_GAMER,),
        )
    )
    shell = ShellModel(router=router)
    shell.set_active_route('capture', role=RoleName.POWER_GAMER)

    shell.mark_failed('some.plugin', reason='unrecoverable-fault')

    assert shell.runtime_state is RuntimeState.FAILED
    assert shell.active_panel_id() == 'panel.capture'
    assert shell.notices
    assert shell.notices[-1].severity == 'error'
    assert 'some.plugin' in shell.degraded_plugins
