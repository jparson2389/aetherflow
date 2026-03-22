from __future__ import annotations

from tools import plan_exec


def test_quality_command_uses_repo_owned_python_entrypoint() -> None:
    assert plan_exec.quality_command(['src/aetherflow/main.py']) == [
        'uv',
        'run',
        'python',
        '-m',
        'tools.check_quality',
        '--paths',
        'src/aetherflow/main.py',
    ]
