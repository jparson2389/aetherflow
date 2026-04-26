from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

ALLOWED_WRITE_PREFIXES: tuple[str, ...] = (
    'src/aetherflow/',
    'include/',
    'host/',
    '.cursor/',
    '.github/',
    'proto/',  # intentional: repo-owned build assets tooling reads proto/ to regenerate stubs
    'assets/',
    'tests/',
    'docs/',
    'state/',
)

ALLOWED_ROOT_FILES: set[str] = {
    'pyproject.toml',
    'README.md',
}
DENIED_WRITE_PATHS: set[str] = {
    'PLAN.md',
    'PRD.md',
    'docs/plan.md',
    'docs/prd.md',
}

PLACEHOLDER_WRITE_PATHS: set[str] = {
    'relative/path',
    'path/to/file',
    'replace/with/real/path.py',
    'file contents',
    'your/path/here',
}


def _norm_path(p: str) -> str:
    return p.replace('\\', '/').strip().lstrip('./').lower()


_DENIED_WRITE_PATHS_NORM: set[str] = {_norm_path(p) for p in DENIED_WRITE_PATHS}
_PLACEHOLDER_WRITE_PATHS_NORM: set[str] = {
    _norm_path(p) for p in PLACEHOLDER_WRITE_PATHS
}
_ALLOWED_ROOT_FILES_NORM: set[str] = {_norm_path(p) for p in ALLOWED_ROOT_FILES}
_ALLOWED_PREFIXES_NORM: tuple[str, ...] = tuple(
    _norm_path(p) for p in ALLOWED_WRITE_PREFIXES
)


@dataclass(frozen=True, slots=True)
class ExistingFileSnapshot:
    """Snapshot of a file that existed before an executor write.

    Attributes:
        path: Repository-relative path for the file.
        sha256: Hex digest of the pre-write bytes.
        content: Decoded pre-write content truncated for prompt reuse.

    """

    path: str
    sha256: str
    content: str


def is_write_path_allowed(path: str) -> bool:
    """Return True if path is permitted by the write allowlist.

    A path is allowed when it is not a placeholder, not explicitly denied,
    and either matches an allowed root file or starts with an allowed prefix.
    """
    raw = path
    p = _norm_path(raw)

    if p in _PLACEHOLDER_WRITE_PATHS_NORM:
        return False
    if p in _DENIED_WRITE_PATHS_NORM:
        return False

    raw_clean = raw.strip().lstrip('./')
    if (
        raw_clean in ALLOWED_ROOT_FILES
        or _norm_path(raw_clean) in _ALLOWED_ROOT_FILES_NORM
    ):
        return True

    return any(p.startswith(prefix) for prefix in _ALLOWED_PREFIXES_NORM)


def validate_writes_payload(payload: dict[str, Any]) -> Any:
    """Validate the writes payload and return the validated model.

    The model has normalized content (e.g. docstring quotes) for .py files.
    """
    try:
        from validation_gate import WritesPayload
    except ModuleNotFoundError:
        from tools.validation_gate import WritesPayload  # type: ignore[no-redef]

    model = WritesPayload.model_validate(payload)
    for entry in model.writes:
        clean = entry.path.strip()
        if not clean:
            raise ValueError('Empty path in write entry.')
        if clean.startswith(('/', '\\')) or re.match(r'^[A-Za-z]:[\\/]', clean):
            raise ValueError(f'Absolute path not allowed: {entry.path!r}')
        normalized = clean.replace('\\', '/').lstrip('./')
        if '/../' in f'/{normalized}/' or normalized in {'..', '.'}:
            raise ValueError(f'Path traversal not allowed: {entry.path!r}')
        if not is_write_path_allowed(clean):
            raise ValueError(f'Path not in allowed locations: {entry.path!r}')
    return model


def _safe_path(repo_root: Path, rel: str) -> Path:
    p = (repo_root / rel).resolve()
    rr = repo_root.resolve()
    if p != rr and rr in p.parents:
        return p
    raise ValueError(f'Refusing to write outside repo root: {rel}')


def capture_existing_file_snapshots(
    repo_root: Path,
    payload: dict[str, Any],
    *,
    max_chars: int = 4000,
) -> dict[str, ExistingFileSnapshot]:
    """Capture pre-write snapshots for files that already exist.

    Args:
        repo_root: Repository root used to resolve relative write paths.
        payload: Validated-or-validatable writes payload.
        max_chars: Maximum decoded content length to retain per file.

    Returns:
        Mapping of repository-relative paths to their pre-write snapshots.

    """
    model = validate_writes_payload(payload)
    snapshots: dict[str, ExistingFileSnapshot] = {}
    for entry in model.writes:
        path = entry.path.strip()
        target = _safe_path(repo_root, path)
        if not target.exists():
            continue
        raw = target.read_bytes()
        text = raw.decode(encoding='utf-8', errors='ignore')
        snapshots[path] = ExistingFileSnapshot(
            path=path,
            sha256=hashlib.sha256(raw).hexdigest(),
            content=text[:max_chars],
        )
    return snapshots


def apply_writes(repo_root: Path, payload: dict[str, Any]) -> list[Path]:
    """Validate payload and write all files to disk under repo_root."""
    model = validate_writes_payload(payload)

    changed: list[Path] = []
    for entry in model.writes:
        path = entry.path.strip()
        content = entry.content

        target = _safe_path(repo_root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        changed.append(target)

    return changed


def main() -> int:
    """CLI entrypoint: read a writes payload and apply it to the repo."""
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', default='.')
    ap.add_argument(
        '--in', dest='infile', default='-', help="JSON file or '-' for stdin"
    )
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()

    if args.infile == '-':
        raw = sys.stdin.read()
    else:
        raw = Path(args.infile).read_text(encoding='utf-8')

    payload = json.loads(raw)
    changed = apply_writes(repo_root, payload)

    for p in changed:
        logger.info(p.relative_to(repo_root))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
