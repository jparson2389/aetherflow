import pytest

from aetherflow.core.entitlements import RoleName
from aetherflow.ui.router import RouteDefinition, RouterModel


def _router_with_route(*, locked: bool = False) -> RouterModel:
    router = RouterModel()
    router.register_route(
        RouteDefinition(
            name='settings',
            title='Settings',
            panel_id='panel.settings',
        )
    )
    if locked:
        router.set_route_lock('settings', reason='maintenance')
    return router


def test_set_route_lock_stores_lock_reason() -> None:
    router = _router_with_route()

    router.set_route_lock('settings', reason='maintenance')

    assert router.routes['settings'].lock_reason == 'maintenance'


def test_is_locked_returns_true_when_lock_reason_set() -> None:
    router = _router_with_route()
    router.set_route_lock('settings', reason='maintenance')

    assert router.routes['settings'].is_locked() is True


def test_navigate_locked_route_raises_permission_error() -> None:
    router = _router_with_route(locked=True)

    with pytest.raises(PermissionError, match='maintenance'):
        router.navigate('settings', role=RoleName.POWER_GAMER)


def test_navigate_succeeds_after_unlocking() -> None:
    router = _router_with_route(locked=True)
    router.set_route_lock('settings', reason=None)

    panel_id = router.navigate('settings', role=RoleName.POWER_GAMER)

    assert panel_id == 'panel.settings'


def test_available_routes_includes_locked_routes() -> None:
    """Locking prevents navigation but not visibility."""
    router = _router_with_route(locked=True)

    visible = router.available_routes(role=RoleName.POWER_GAMER)

    assert any(r.name == 'settings' for r in visible)
