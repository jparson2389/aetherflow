from aetherflow.core.entitlements import (
    EntitlementState,
    EntitlementStore,
    RoleName,
    UserRole,
)


def test_entitlement_store_locks_missing_premium_access() -> None:
    store = EntitlementStore()

    state = store.evaluate('capture.premium', ('vision',))

    assert state is EntitlementState.LOCKED


def test_entitlement_store_resolves_grace_before_lock() -> None:
    store = EntitlementStore()
    store.activate_grace('capture.premium', ('vision',))

    state = store.evaluate('capture.premium', ('vision',))

    assert state is EntitlementState.GRACE


def test_role_capabilities_are_explicit() -> None:
    role = UserRole(name=RoleName.VISION_ML_TINKERER)

    assert 'env.manage' in role.capabilities
    assert 'admin.manage_users' not in role.capabilities
