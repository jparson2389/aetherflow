"""Shell bootstrap tests (no Qt; run on all platforms)."""

from __future__ import annotations

from aetherflow.core.entitlements import RoleName
from aetherflow.main import build_shell


def test_build_shell_registers_default_routes_and_hud() -> None:
    """Build a shell with visible startup routes and an attached HUD."""

    shell = build_shell()

    visible_routes = shell.router.available_routes(role=RoleName.POWER_GAMER)

    assert shell.status_hud is not None
    assert shell.active_panel_id() == 'panel.home'
    assert [route.name for route in visible_routes] == [
        'home',
        'catalog',
        'capture',
        'output',
        'workers',
    ]


def test_build_shell_uses_active_role_for_default_routes() -> None:
    """Build a shell whose startup route visibility matches the active role."""

    shell = build_shell(role=RoleName.ADMIN_OPERATOR)

    visible_routes = shell.router.available_routes(role=RoleName.ADMIN_OPERATOR)

    assert shell.active_panel_id() == 'panel.home'
    assert [route.name for route in visible_routes] == [
        'home',
        'catalog',
        'capture',
        'output',
        'workers',
        'environment',
        'resources',
        'admin',
    ]
