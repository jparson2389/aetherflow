from __future__ import annotations

from tools import plan_exec


def test_build_assets_command_uses_repo_owned_python_entrypoint() -> None:
    assert plan_exec.build_assets_command() == [
        'uv',
        'run',
        'python',
        '-m',
        'tools.build_assets',
    ]
