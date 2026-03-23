"""Atomic JSON persistence for input profiles."""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from aetherflow.core.profiles import ProfileStore


class ProfileRepository:
    """Load and save profile stores as JSON files with atomic writes."""

    def __init__(self, path: Path | None = None) -> None:
        """Create a repository backed by a JSON file.

        Args:
            path: File path for persistence. Defaults to data/input_profiles.json.

        """
        self._path = path or Path('data/input_profiles.json')

    def load(self) -> ProfileStore:
        """Load profiles from disk.

        Returns:
            A ProfileStore populated from the JSON file, or an empty store
            if the file does not exist.

        """
        if not self._path.exists():
            return ProfileStore()

        try:
            raw = json.loads(self._path.read_text(encoding='utf-8'))
            store = ProfileStore()
            for payload in raw.get('profiles', []):
                store.import_profile(payload)
            active_id = raw.get('active_profile_id')
            if active_id and active_id in store.profiles:
                store.switch_active(active_id)
            return store
        except Exception:  # JSONDecodeError, KeyError, TypeError, or IO error
            logger.warning(
                'ProfileRepository: could not load {}; starting with empty store.',
                self._path,
            )
            return ProfileStore()

    def save(self, store: ProfileStore) -> None:
        """Atomically save profiles to disk.

        Args:
            store: The profile store to persist.

        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'active_profile_id': store.active_profile_id,
            'profiles': [
                store.export_profile(pid) for pid in store.profiles
            ],
        }
        tmp = self._path.with_suffix('.tmp')
        tmp.write_text(
            json.dumps(payload, indent=2),
            encoding='utf-8',
        )
        tmp.replace(self._path)
