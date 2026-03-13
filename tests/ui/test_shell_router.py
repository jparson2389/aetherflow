from aetherflow.core.entitlements import RoleName
from aetherflow.core.runtime_state import RuntimeState
from aetherflow.ui.router import RouteDefinition, RouterModel
from aetherflow.ui.shell import ShellModel


def test_router_filters_and_navigates() -> None:
    """Verify routes filter by role and navigation activates panels."""
    router = RouterModel()
    router.register_route(
        RouteDefinition(
            name='catalog',
            title='Catalog',
            panel_id='panel.catalog',
            allowed_roles=(RoleName.POWER_GAMER,),
        )
    )
    router.register_route(
        RouteDefinition(
            name='admin',
            title='Admin',
            panel_id='panel.admin',
            allowed_roles=(RoleName.ADMIN_OPERATOR,),
        )
    )

    visible = router.available_routes(role=RoleName.POWER_GAMER)

    assert [route.name for route in visible] == ['catalog']
    assert router.navigate('catalog') == 'panel.catalog'
    assert router.active_panel_id() == 'panel.catalog'

    router.mark_failed('catalog', reason='panel-crash')
    assert router.failed_routes['catalog'] == 'panel-crash'


def test_shell_tracks_active_routes_and_degradation() -> None:
    """Ensure shell state tracks active panels and degradations."""
    router = RouterModel()
    router.register_route(
        RouteDefinition(
            name='catalog',
            title='Catalog',
            panel_id='panel.catalog',
        )
    )
    shell = ShellModel(router=router)

    assert shell.set_active_route('catalog') == 'panel.catalog'
    assert shell.active_panel_id() == 'panel.catalog'

    shell.mark_degraded('capture.opencv')

    assert shell.runtime_state is RuntimeState.DEGRADED
    assert 'capture.opencv' in shell.degraded_plugins
