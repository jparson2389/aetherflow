"""Application entrypoints for Aetherflow."""

from loguru import logger

from aetherflow.core.dotenv_bootstrap import configure_environment


def main() -> int:
    """Run the minimal Aetherflow shell entrypoint.

    Returns:
        Process exit code.

    """
    configure_environment()
    logger.info('Starting Aetherflow shell bootstrap.')
    return 0
