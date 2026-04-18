from __future__ import annotations

import re
import subprocess
from pathlib import Path

from loguru import logger

# grpc_tools emits `import foo_pb2` for sibling modules; that only resolves when the
# output directory is a sys.path root. The aetherflow package layout needs relative
# imports between generated siblings (see grpc/grpc#29459 and related issues).
_GRPC_SIBLING_PB2_IMPORT = re.compile(
    r'^import (?P<mod>[A-Za-z_]\w*_pb2) as (?P<alias>[A-Za-z_]\w*)\s*$',
    re.MULTILINE,
)

ROOT = Path(__file__).resolve().parents[1]


def _run_command(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run an asset build command and capture combined output."""
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _grpc_stub_sibling_imports_package_relative(out_dir: Path) -> None:
    """Rewrite grpc_python sibling imports so ``aetherflow.proto.*`` imports work."""
    for path in sorted(out_dir.glob('*_pb2_grpc.py')):
        text = path.read_text(encoding='utf-8')
        new = _GRPC_SIBLING_PB2_IMPORT.sub(r'from . import \g<mod> as \g<alias>', text)
        if new != text:
            path.write_text(new, encoding='utf-8')
            logger.debug('Adjusted sibling pb2 imports in {}.', path.name)


def _ensure_proto_package(out_dir: Path) -> None:
    """Ensure generated protobuf output is importable as a Python package."""
    out_dir.mkdir(parents=True, exist_ok=True)
    init_path = out_dir / '__init__.py'
    if not init_path.exists():
        init_path.write_text(
            '"""Generated protobuf and gRPC modules."""\n',
            encoding='utf-8',
        )


def compile_proto_assets(repo_root: Path) -> None:
    """Compile tracked proto definitions into Python protobuf/gRPC modules."""
    proto_dir = repo_root / 'proto'
    proto_files = sorted(proto_dir.glob('*.proto'))
    if not proto_files:
        logger.info(
            'No .proto files found under {}. Skipping gRPC compilation.', proto_dir
        )
        return

    out_dir = repo_root / 'src' / 'aetherflow' / 'proto'
    _ensure_proto_package(out_dir)

    command = [
        'uv',
        'run',
        'python',
        '-m',
        'grpc_tools.protoc',
        f'-I{proto_dir}',
        f'--python_out={out_dir}',
        f'--grpc_python_out={out_dir}',
        *[str(proto_file) for proto_file in proto_files],
    ]
    result = _run_command(command, cwd=repo_root)
    if result.returncode != 0:
        raise RuntimeError(
            'gRPC compilation failed:\n'
            f'{(result.stdout or "")}{(result.stderr or "")}'.strip()
        )
    _grpc_stub_sibling_imports_package_relative(out_dir)
    logger.info('Compiled {} proto file(s) into {}.', len(proto_files), out_dir)


def compile_ui_assets(repo_root: Path) -> None:
    """Compile Qt Designer .ui files into Python modules when present."""
    ui_dir = repo_root / 'assets' / 'ui'
    ui_files = sorted(ui_dir.glob('*.ui'))
    if not ui_files:
        logger.info('No UI files found under {}. Skipping UI compilation.', ui_dir)
        return

    out_dir = repo_root / 'src' / 'aetherflow'
    out_dir.mkdir(parents=True, exist_ok=True)
    for ui_file in ui_files:
        command = [
            'uv',
            'run',
            'pyside6-uic',
            str(ui_file),
            '-o',
            str(out_dir / f'ui_{ui_file.stem}.py'),
        ]
        result = _run_command(command, cwd=repo_root)
        if result.returncode != 0:
            raise RuntimeError(
                f'UI compilation failed for {ui_file}:\n'
                f'{(result.stdout or "")}{(result.stderr or "")}'.strip()
            )
    logger.info('Compiled {} UI file(s).', len(ui_files))


def main() -> int:
    """Build generated project assets from tracked source inputs."""
    compile_proto_assets(ROOT)
    compile_ui_assets(ROOT)
    logger.info('Build complete.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
