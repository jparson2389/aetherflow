"""Helpers for loading environment variables from dotenv files."""

from __future__ import annotations

from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from loguru import logger

DEFAULT_DOTENV_FILENAME = '.env'


def _find_repo_root() -> Path | None:
    candidate = Path(__file__).resolve().parent
    while candidate != candidate.parent:
        if (candidate / 'pyproject.toml').is_file():
            return candidate
        candidate = candidate.parent
    return None


REPO_ROOT: Path | None = _find_repo_root()
DEFAULT_ENV_FILE: Path | None = (
    REPO_ROOT / DEFAULT_DOTENV_FILENAME if REPO_ROOT is not None else None
)


def configure_environment(
    env_file: Path | None = None,
    *,
    override: bool = False,
) -> Path | None:
    """Load environment variables from a dotenv file when present.

    Args:
        env_file: Optional explicit path to the dotenv file.
        override: Whether values from the dotenv file should replace
            existing process environment variables.

    Returns:
        The resolved dotenv path when one was loaded, otherwise ``None``.

    """
    dotenv_path = resolve_dotenv_path(env_file)
    if dotenv_path is None:
        logger.debug(
            'No {} file found. Using process environment.', DEFAULT_DOTENV_FILENAME
        )
        return None

    load_dotenv(dotenv_path=dotenv_path, override=override)
    logger.debug('Loaded environment variables from {}.', dotenv_path)
    return dotenv_path


def resolve_dotenv_path(env_file: Path | None = None) -> Path | None:
    """Resolve the dotenv file path for the current process.

    Args:
        env_file: Optional explicit dotenv path.

    Returns:
        The resolved dotenv file path when one exists, otherwise ``None``.

    """
    if env_file is not None:
        candidate = env_file.expanduser().resolve()
        return candidate if candidate.is_file() else None

    if DEFAULT_ENV_FILE is not None and DEFAULT_ENV_FILE.is_file():
        return DEFAULT_ENV_FILE

    discovered = find_dotenv(filename=DEFAULT_DOTENV_FILENAME, usecwd=True)
    if not discovered:
        return None

    return Path(discovered).resolve()
