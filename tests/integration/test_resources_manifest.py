from __future__ import annotations

import json
from base64 import b64encode
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aetherflow.core.resources_client import ResourcesClient
from aetherflow.core.resources_manifest import ResourceEntry, ResourceManifest

TEST_KEY_ID = 'test-key-1'
TEST_PRIVATE_KEY_BYTES = bytes(range(1, 33))


def _write_trust_store(path: Path) -> None:
    public_key = (
        Ed25519PrivateKey.from_private_bytes(TEST_PRIVATE_KEY_BYTES)
        .public_key()
        .public_bytes_raw()
    )
    payload = {
        'active_key_id': TEST_KEY_ID,
        'keys': [
            {
                'key_id': TEST_KEY_ID,
                'algorithm': 'ed25519',
                'public_key': b64encode(public_key).decode('ascii'),
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def _sign_manifest(version: str, resources: list[ResourceEntry]) -> str:
    payload = {
        'resources': [
            {
                'kind': entry.kind,
                'premium': entry.premium,
                'required_tier': entry.required_tier,
                'resource_id': entry.resource_id,
                'sha256': entry.sha256,
                'size': entry.size,
                'version': entry.version,
            }
            for entry in resources
        ],
        'signing_key_id': TEST_KEY_ID,
        'version': version,
    }
    private_key = Ed25519PrivateKey.from_private_bytes(TEST_PRIVATE_KEY_BYTES)
    return b64encode(
        private_key.sign(
            json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
        )
    ).decode('ascii')


def test_resources_client_rejects_manifest_with_structure_errors(
    tmp_path: Path,
) -> None:
    trust_store_path = tmp_path / 'trust_store.json'
    _write_trust_store(trust_store_path)
    client = ResourcesClient(trust_store_path=trust_store_path)
    manifest = ResourceManifest(
        version='1.0',
        signature='',
        signing_key_id='',
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

    result = client.validate_manifest(manifest)

    assert result.valid is False
    assert 'missing-signature' in result.reason_codes
    assert 'missing-signing-key-id' in result.reason_codes


def test_resources_client_rejects_premium_without_required_tier(
    tmp_path: Path,
) -> None:
    trust_store_path = tmp_path / 'trust_store.json'
    _write_trust_store(trust_store_path)
    client = ResourcesClient(trust_store_path=trust_store_path)
    resources = [
        ResourceEntry(
            resource_id='profile.premium',
            kind='profile',
            version='1.0.0',
            sha256='a' * 64,
            size=16,
            premium=True,
            required_tier=None,
        )
    ]
    manifest = ResourceManifest(
        version='1.0',
        signature=_sign_manifest('1.0', resources),
        signing_key_id=TEST_KEY_ID,
        resources=resources,
    )

    result = client.validate_manifest(manifest)

    assert result.valid is False
    assert 'missing-required-tier' in result.reason_codes


def test_resources_client_rejects_unknown_signing_key(tmp_path: Path) -> None:
    trust_store_path = tmp_path / 'trust_store.json'
    _write_trust_store(trust_store_path)
    client = ResourcesClient(trust_store_path=trust_store_path)
    resources = [
        ResourceEntry(
            resource_id='profile.default',
            kind='profile',
            version='1.0.0',
            sha256='a' * 64,
            size=32,
            premium=False,
        )
    ]
    manifest = ResourceManifest(
        version='1.0',
        signature=_sign_manifest('1.0', resources),
        signing_key_id='unknown',
        resources=resources,
    )

    result = client.validate_manifest(manifest)

    assert result.valid is False
    assert 'unknown-signing-key' in result.reason_codes


def test_resources_client_accepts_trusted_manifest(tmp_path: Path) -> None:
    trust_store_path = tmp_path / 'trust_store.json'
    _write_trust_store(trust_store_path)
    client = ResourcesClient(trust_store_path=trust_store_path)
    resources = [
        ResourceEntry(
            resource_id='profile.default',
            kind='profile',
            version='1.0.0',
            sha256='a' * 64,
            size=32,
            premium=False,
        )
    ]
    manifest = ResourceManifest(
        version='1.0',
        signature=_sign_manifest('1.0', resources),
        signing_key_id=TEST_KEY_ID,
        resources=resources,
    )

    result = client.validate_manifest(manifest)

    assert result.valid is True
    assert result.reason_codes == ()
