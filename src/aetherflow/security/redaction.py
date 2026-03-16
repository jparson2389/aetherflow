"""Redaction helpers for diagnostics and audit exports."""

from __future__ import annotations

import re
from collections.abc import Mapping

_REDACTION = '[REDACTED]'
_BEARER_TOKEN_RE = re.compile(r'(?i)(bearer\s+)([A-Za-z0-9._\-]+)')
_OPENAI_KEY_RE = re.compile(r'\bsk-[A-Za-z0-9_-]+\b')
_JWT_RE = re.compile(
    r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+\b'
)
_URL_USERINFO_RE = re.compile(r'://([^:/\s]+):([^@/\s]+)@')
_OPAQUE_SECRET_RE = re.compile(
    r'(?i)\b(authorization|api[_-]?key|token|secret|password)\b\s*[:=]\s*([^\s,;]+)'
)


def redact_sensitive_text(value: str) -> str:
    """Redact secret-like substrings from free-form text.

    Args:
        value: Raw text to sanitize.

    Returns:
        Redacted text safe to export.

    """
    redacted = _BEARER_TOKEN_RE.sub(rf'\1{_REDACTION}', value)
    redacted = _OPENAI_KEY_RE.sub(_REDACTION, redacted)
    redacted = _JWT_RE.sub(_REDACTION, redacted)
    redacted = _URL_USERINFO_RE.sub(f'://{_REDACTION}@', redacted)
    redacted = _OPAQUE_SECRET_RE.sub(rf'\1={_REDACTION}', redacted)
    return redacted


def redact_sensitive_mapping(payload: Mapping[str, object]) -> dict[str, object]:
    """Return a shallow mapping copy with secret-like values redacted.

    Args:
        payload: Mapping to sanitize.

    Returns:
        Sanitized dictionary.

    """
    sanitized: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            sanitized[key] = redact_sensitive_text(value)
        elif isinstance(value, Mapping):
            sanitized[key] = redact_sensitive_mapping(value)
        elif isinstance(value, list):
            sanitized[key] = [
                redact_sensitive_mapping(item)
                if isinstance(item, Mapping)
                else redact_sensitive_text(item)
                if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized
