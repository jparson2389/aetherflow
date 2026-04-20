"""Shared signed-bundle helpers for unit and integration tests."""

from __future__ import annotations

import hashlib
import json
from base64 import b64encode
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aetherflow.core.bundle_installer import BundleManifest

TEST_KEY_ID = 'test-key-1'
TEST_PRIVATE_KEY_BYTES = bytes(range(1, 33))


def write_test_trust_store(path: Path) -> None:
    """Persist the public manifest signing key used in tests."""
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


def build_test_manifest(
    *,
    archive_path: Path,
    trust_store_path: Path,
    bundle_id: str,
    version: str = '1.0.0',
    python_version: str = '3.12',
    dependencies: list[str] | None = None,
) -> BundleManifest:
    """Build a signed bundle manifest for an on-disk archive."""
    deps = dependencies or []
    archive_bytes = archive_path.read_bytes()
    unsigned = {
        'archive_size_bytes': len(archive_bytes),
        'bundle_id': bundle_id,
        'dependencies': sorted(deps),
        'version': version,
        'python_version': python_version,
        'sha256': hashlib.sha256(archive_bytes).hexdigest(),
        'signing_key_id': TEST_KEY_ID,
    }
    private_key = Ed25519PrivateKey.from_private_bytes(TEST_PRIVATE_KEY_BYTES)
    signature = b64encode(
        private_key.sign(
            json.dumps(unsigned, separators=(',', ':'), sort_keys=True).encode('utf-8')
        )
    ).decode('ascii')
    write_test_trust_store(trust_store_path)
    return BundleManifest(
        archive_size_bytes=unsigned['archive_size_bytes'],
        bundle_id=bundle_id,
        dependencies=deps,
        sha256=unsigned['sha256'],
        signature=signature,
        signing_key_id=TEST_KEY_ID,
        version=version,
        python_version=python_version,
    )
