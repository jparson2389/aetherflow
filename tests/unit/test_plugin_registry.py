from aetherflow.core.entitlements import EntitlementState, RoleName, UserRole
from aetherflow.core.services import create_default_services
from aetherflow.plugins.catalog import CatalogLockState
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion
from aetherflow.plugins.registry import PluginRegistry

DEFAULT_SIGNATURE = {
    'signature_scheme': 'Authenticode',
    'digest_algorithm': 'SHA-256',
    'rsa_key_bits': 3072,
    'publisher_thumbprint': 'aetherflow-publisher',
    'trust_root_thumbprint': 'aetherflow-root',
}


def make_manifest(
    plugin_id: str,
    *,
    premium: bool = False,
    signed: bool = True,
) -> PluginManifest:
    return PluginManifest(
        plugin_id=plugin_id,
        name=plugin_id.replace('.', ' ').title(),
        version=PluginVersion.parse('1.0.0'),
        api_version='1.0',
        plugin_type=PluginType.CAPTURE,
        entrypoint=f'{plugin_id}.dll',
        signed=signed,
        premium=premium,
        required_entitlements=['vision'] if premium else [],
        requires_worker=False,
        **DEFAULT_SIGNATURE,
    )


def test_registry_blocks_unsigned_plugins() -> None:
    services = create_default_services()
    registry = PluginRegistry(services=services)

    result = registry.register(make_manifest('capture.unsigned', signed=False))
    entry = registry.catalog()[0]

    assert result.loaded is False
    assert result.reason == 'unsigned-plugin'
    assert entry.lock_reason == 'unsigned-plugin'
    assert entry.entitlement_state is EntitlementState.LOCKED
    assert entry.plugin_type is PluginType.CAPTURE
    assert entry.version == '1.0.0'


def test_registry_blocks_locked_premium_plugins() -> None:
    services = create_default_services()
    registry = PluginRegistry(services=services)

    result = registry.register(make_manifest('capture.premium', premium=True))
    entry = registry.catalog()[0]

    assert result.loaded is False
    assert result.state is EntitlementState.LOCKED
    assert entry.lock_state is CatalogLockState.LOCKED
    assert entry.lock_reason == 'locked-premium-plugin'
    assert entry.premium is True
    assert entry.required_entitlements == ('vision',)


def test_registry_loads_premium_plugins_in_grace_state() -> None:
    services = create_default_services()
    services.entitlements.activate_grace(
        plugin_id='capture.premium',
        required_entitlements=('vision',),
    )
    registry = PluginRegistry(services=services)

    result = registry.register(make_manifest('capture.premium', premium=True))
    entry = registry.catalog()[0]

    assert result.loaded is True
    assert result.state is EntitlementState.GRACE
    assert entry.lock_state is CatalogLockState.GRACE
    assert entry.entitlement_state is EntitlementState.GRACE
    assert entry.lock_reason is None


def test_catalog_visibility_respects_roles() -> None:
    services = create_default_services(
        roles=[
            UserRole(name=RoleName.POWER_GAMER),
            UserRole(name=RoleName.ADMIN_OPERATOR),
        ]
    )
    registry = PluginRegistry(services=services)
    registry.register(make_manifest('capture.basic'))

    visible = registry.catalog_for_role(RoleName.POWER_GAMER)
    admin_visible = registry.catalog_for_role(RoleName.ADMIN_OPERATOR)

    assert len(visible) == 1
    assert len(admin_visible) == 1
    assert admin_visible[0].allowed_roles[-1] is RoleName.ADMIN_OPERATOR
