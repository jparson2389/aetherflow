from __future__ import annotations

from pathlib import Path

from tools.validation_gate import run_validation_command


def test_validation_gate_rejects_shell_metacharacters(tmp_path: Path) -> None:
    result = run_validation_command(tmp_path, 'uv run pytest ; whoami')

    assert result.passed is False
    assert 'disallowed command syntax' in result.errors[0].lower()


def test_validation_gate_allows_pytest_command(tmp_path: Path) -> None:
    test_path = tmp_path / 'test_ok.py'
    test_path.write_text('def test_ok() -> None:\n    assert True\n', encoding='utf-8')

    result = run_validation_command(
        tmp_path,
        f'uv run pytest {test_path.name}',
    )

    assert result.passed is True
