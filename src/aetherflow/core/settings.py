"""Typed runtime settings for security-sensitive paths."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AetherflowSettings(BaseSettings):
    """Configuration values for trust and audit components.

    Attributes:
        manifest_trust_store_path: Default path to the JSON manifest trust
            store.
        admin_audit_log_path: Default append-only audit log location.

    """

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_prefix='AETHERFLOW_',
        extra='ignore',
    )

    manifest_trust_store_path: Path = Field(
        default=Path('assets/trust/manifest_keys.json')
    )
    admin_audit_log_path: Path = Field(default=Path('logs/admin_audit.ndjson'))
