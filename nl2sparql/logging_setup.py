"""Logging configuration shared by every command line script."""

import json
import logging

from nl2sparql.config import get_log_level
from nl2sparql.errors import ConfigurationError



class JsonLogFormatter(logging.Formatter):
    """Serialize each log record as one JSON object per line."""

    def format(self, record):
        fields = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "component": record.name,
            "event": record.getMessage(),
        }
        if record.exc_info:
            fields["exception"] = self.formatException(record.exc_info)
        return json.dumps(fields)


def configure_logging(level_name=None):
    """Configure root logging from the LOG_LEVEL environment variable."""
    level_name = level_name or get_log_level()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        raise ConfigurationError(f"LOG_LEVEL is not a valid level: {level_name!r}")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logging.basicConfig(level=level, handlers=[handler])
