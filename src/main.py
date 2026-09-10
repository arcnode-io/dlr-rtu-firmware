"""Main entry point for the application."""

import asyncio
import logging

from build import CONFIG
from src import app


async def main() -> None:
    """Execute the main entry point of the application.

    Load configuration, set up logging, and run the app.

    Example:
        >>> asyncio.run(main())  # Loads config and runs app with temperature sensor

    """
    # Reason: CONFIG.log_level was defined in cfg.yml but never wired to the
    # logging module -- every _log.debug/.info call was silently dropped.
    logging.basicConfig(
        level=CONFIG.log_level.value,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.info("Hardware initialized. Starting application...")

    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
