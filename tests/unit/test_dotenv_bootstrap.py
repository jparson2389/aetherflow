from __future__ import annotations

import os
from pathlib import Path

import pytest

from aetherflow import main as main_module


def test_configure_environment_loads_variables_from_discovered_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = tmp_path / '.env'
    env_path.write_text('AETHERFLOW_TEST_FLAG=enabled\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('AETHERFLOW_TEST_FLAG', raising=False)

    from aetherflow.core.dotenv_bootstrap import configure_environment

    loaded_path = configure_environment()

    assert loaded_path == env_path.resolve()
    assert os.environ['AETHERFLOW_TEST_FLAG'] == 'enabled'


def test_configure_environment_does_not_override_existing_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = tmp_path / '.env'
    env_path.write_text('AETHERFLOW_TEST_FLAG=from-dotenv\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('AETHERFLOW_TEST_FLAG', 'from-process')

    from aetherflow.core.dotenv_bootstrap import configure_environment

    loaded_path = configure_environment()

    assert loaded_path == env_path.resolve()
    assert os.environ['AETHERFLOW_TEST_FLAG'] == 'from-process'


def test_main_loads_dotenv_during_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_configure_environment() -> Path | None:
        calls.append('configured')
        return None

    monkeypatch.setattr(
        main_module,
        'configure_environment',
        fake_configure_environment,
        raising=False,
    )
    monkeypatch.setattr(main_module.logger, 'info', lambda *_args, **_kwargs: None)

    result = main_module.main()

    assert result == 0
    assert calls == ['configured']
