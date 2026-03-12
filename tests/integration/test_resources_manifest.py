from aetherflow.core.resources_client import ResourcesClient
from aetherflow.core.resources_manifest import ResourceEntry, ResourceManifest


def test_resources_client_rejects_manifest_with_policy_errors() -> None:
    client = ResourcesClient()
    manifest = ResourceManifest(
        version='1.0',
        signature='',
        signature_scheme='Unknown',
        digest_algorithm='MD5',
        rsa_key_bits=1024,
        publisher_thumbprint='',
        trust_root_thumbprint='',
        resources=[
            ResourceEntry(
                resource_id='profile.default',
                kind='profile',
                version='1.0.0',
                sha256='abc',
                size=-1,
                premium=True,
            )
        ],
    )

    assert client.validate_manifest(manifest) is False


def test_resources_client_rejects_premium_without_required_tier() -> None:
    client = ResourcesClient()
    manifest = ResourceManifest(
        version='1.0',
        signature='signed',
        signature_scheme='Authenticode',
        digest_algorithm='SHA-256',
        rsa_key_bits=3072,
        publisher_thumbprint='aetherflow-publisher',
        trust_root_thumbprint='aetherflow-root',
        resources=[
            ResourceEntry(
                resource_id='profile.premium',
                kind='profile',
                version='1.0.0',
                sha256='a' * 64,
                size=16,
                premium=True,
                required_tier=None,
            )
        ],
    )

    assert client.validate_manifest(manifest) is False


def test_resources_client_accepts_trusted_manifest() -> None:
    client = ResourcesClient()
    manifest = ResourceManifest(
        version='1.0',
        signature='signed',
        signature_scheme='Authenticode',
        digest_algorithm='SHA-256',
        rsa_key_bits=3072,
        publisher_thumbprint='aetherflow-publisher',
        trust_root_thumbprint='aetherflow-root',
        resources=[
            ResourceEntry(
                resource_id='profile.default',
                kind='profile',
                version='1.0.0',
                sha256='a' * 64,
                size=32,
                premium=False,
            )
        ],
    )

    assert client.validate_manifest(manifest) is True
