from aetherflow.core.entitlements import RoleName
from aetherflow.core.runtime_state import RuntimeState
from aetherflow.main import build_shell
from aetherflow.ui.router import RouteDefinition, RouteEventType, RouterModel
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
    assert router.navigate('catalog', role=RoleName.POWER_GAMER) == 'panel.catalog'
    assert router.active_panel_id() == 'panel.catalog'
    assert router.events[-1].status is RouteEventType.ACTIVATED

    router.mark_failed('catalog', reason='panel-crash')
    assert router.failed_routes['catalog'] == 'panel-crash'
    assert router.events[-1].status is RouteEventType.FAILED
    assert router.events[-1].reason == 'panel-crash'


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

    assert (
        shell.set_active_route('catalog', role=RoleName.POWER_GAMER) == 'panel.catalog'
    )
    assert shell.active_panel_id() == 'panel.catalog'

    shell.mark_degraded('capture.opencv')

    assert shell.runtime_state is RuntimeState.DEGRADED
    assert 'capture.opencv' in shell.degraded_plugins


def test_shell_records_route_failures() -> None:
    """Ensure shell logs route failures and notices."""
    router = RouterModel()
    router.register_route(
        RouteDefinition(
            name='admin',
            title='Admin',
            panel_id='panel.admin',
        )
    )
    shell = ShellModel(router=router)

    shell.record_route_failure('admin', reason='panel-crash')

    assert router.failed_routes['admin'] == 'panel-crash'
    assert shell.runtime_state is RuntimeState.DEGRADED
    assert shell.notices[-1].message == 'Route failed: admin'


def test_router_rejects_unauthorized_navigation() -> None:
    router = RouterModel()
    router.register_route(
        RouteDefinition(
            name='admin',
            title='Admin',
            panel_id='panel.admin',
            allowed_roles=(RoleName.ADMIN_OPERATOR,),
        )
    )

    try:
        router.navigate('admin', role=RoleName.POWER_GAMER)
    except PermissionError as exc:
        assert 'admin' in str(exc).lower()
    else:
        raise AssertionError('Expected unauthorized navigation to fail.')


def test_build_shell_loads_pending_app_check_notices(monkeypatch, tmp_path) -> None:
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

    assert len(shell.notices) == 1
    assert 'check for functionality' in shell.notices[0].message.lower()
