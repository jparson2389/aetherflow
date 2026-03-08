"""Application entrypoints for Aetherflow."""

from loguru import logger


def main() -> int:
    """Run the minimal Aetherflow shell entrypoint.

    Returns:
        Process exit code.

    """
    logger.info("Starting Aetherflow shell bootstrap.")
    return 0
