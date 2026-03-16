"""Detached manifest signature verification helpers."""

from __future__ import annotations

import json
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from aetherflow.core.settings import AetherflowSettings


@dataclass(frozen=True, slots=True)
class SignatureVerificationResult:
    """Signature verification outcome."""

    valid: bool
    reason: str | None = None


def canonicalize_payload(payload: dict[str, Any]) -> bytes:
    """Return canonical JSON bytes for a detached signature payload.

    Args:
        payload: Manifest payload without the detached signature field.

    Returns:
        Canonical UTF-8 encoded JSON bytes.

    """
    return json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')


def resolve_manifest_trust_store_path(trust_store_path: Path | None = None) -> Path:
    """Resolve the effective trust store path.

    Args:
        trust_store_path: Optional override.

    Returns:
        Effective filesystem path to the JSON trust store.

    """
    if trust_store_path is not None:
        return trust_store_path
    return AetherflowSettings().manifest_trust_store_path


def verify_manifest_signature(
    *,
    payload: dict[str, Any],
    signature: str,
    signing_key_id: str,
    trust_store_path: Path | None = None,
) -> SignatureVerificationResult:
    """Verify a detached Ed25519 manifest signature.

    Args:
        payload: Canonicalizable manifest payload without signature data.
        signature: Base64-encoded detached signature.
        signing_key_id: Key identifier expected in the trust store.
        trust_store_path: Optional trust store override.

    Returns:
        Signature verification outcome.

    """
    if not signature:
        return SignatureVerificationResult(valid=False, reason='missing-signature')
    if not signing_key_id:
        return SignatureVerificationResult(valid=False, reason='missing-signing-key-id')
    store_path = resolve_manifest_trust_store_path(trust_store_path)
    if not store_path.exists():
        return SignatureVerificationResult(valid=False, reason='missing-trust-store')

    store = json.loads(store_path.read_text(encoding='utf-8'))
    keys = {
        entry['key_id']: entry
        for entry in store.get('keys', [])
        if isinstance(entry, dict) and entry.get('key_id')
    }
    key_entry = keys.get(signing_key_id)
    if key_entry is None:
        return SignatureVerificationResult(valid=False, reason='unknown-signing-key')
    if key_entry.get('algorithm') != 'ed25519':
        return SignatureVerificationResult(valid=False, reason='unsupported-algorithm')

    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            b64decode(key_entry['public_key'])
        )
        public_key.verify(b64decode(signature), canonicalize_payload(payload))
    except (InvalidSignature, ValueError, TypeError, KeyError):
        return SignatureVerificationResult(valid=False, reason='invalid-signature')

    return SignatureVerificationResult(valid=True)
