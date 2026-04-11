"""Main entry point for the application."""

import asyncio
import logging

from src import app


async def main() -> None:
    """Execute the main entry point of the application.

    Load configuration, set up logging, and run the app.

    Example:
        >>> asyncio.run(main())  # Loads config and runs app with temperature sensor

    """
    logging.info("Hardware initialized. Starting application...")

    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
