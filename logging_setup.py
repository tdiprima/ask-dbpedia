"""Logging configuration shared by every command line script."""

import logging

from config import get_log_level
from errors import ConfigurationError

LOG_FORMAT = (
    '{"time": "%(asctime)s", "level": "%(levelname)s", '
    '"component": "%(name)s", "event": "%(message)s"}'
)


def configure_logging():
    """Configure root logging from the LOG_LEVEL environment variable."""
    level_name = get_log_level()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        raise ConfigurationError(f"LOG_LEVEL is not a valid level: {level_name!r}")
    logging.basicConfig(level=level, format=LOG_FORMAT)
