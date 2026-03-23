from pathlib import Path

from aetherflow.core.profile_persistence import ProfileRepository
from aetherflow.core.profiles import ProfileStore


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / 'profiles.json'
    store = ProfileStore()
    profile = store.create('Default')
    profile.button_map['KEY_A'] = 'JUMP'

    repo = ProfileRepository(path=path)
    repo.save(store)

    loaded = repo.load()
    assert len(loaded.profiles) == 1
    loaded_profile = next(iter(loaded.profiles.values()))
    assert loaded_profile.name == 'Default'
    assert loaded_profile.button_map['KEY_A'] == 'JUMP'


def test_load_missing_file_returns_empty_store(tmp_path: Path) -> None:
    path = tmp_path / 'nonexistent.json'
    repo = ProfileRepository(path=path)
    store = repo.load()
    assert len(store.profiles) == 0
    assert store.active_profile_id is None


def test_save_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / 'nested' / 'dir' / 'profiles.json'
    store = ProfileStore()
    store.create('Test')

    repo = ProfileRepository(path=path)
    repo.save(store)

    assert path.exists()


def test_load_malformed_json_returns_empty_store(tmp_path: Path) -> None:
    path = tmp_path / 'profiles.json'
    path.write_text('{not valid json', encoding='utf-8')

    repo = ProfileRepository(path=path)
    store = repo.load()

    assert len(store.profiles) == 0
    assert store.active_profile_id is None


def test_load_truncated_json_returns_empty_store(tmp_path: Path) -> None:
    path = tmp_path / 'profiles.json'
    path.write_text('{"profiles": [{"profile_id": 1}]}', encoding='utf-8')

    repo = ProfileRepository(path=path)
    store = repo.load()

    assert len(store.profiles) == 0


def test_active_profile_preserved_on_round_trip(tmp_path: Path) -> None:
    path = tmp_path / 'profiles.json'
    store = ProfileStore()
    p1 = store.create('First')
    p2 = store.create('Second')
    store.switch_active(p2.profile_id)

    repo = ProfileRepository(path=path)
    repo.save(store)
    loaded = repo.load()

    assert loaded.active_profile_id == p2.profile_id
