"""Standalone generate demonstration."""
import logging
from nl2sparql.config import load_settings
from nl2sparql.errors import Nl2SparqlError
from nl2sparql.logging_setup import configure_logging
from nl2sparql.openai_backend import generate_sparql, EXAMPLE_NATURAL_QUERY
from nl2sparql.display import write_line


def main():
    try:
        settings = load_settings("openai")
        configure_logging(settings.log_level)
        write_line(generate_sparql(EXAMPLE_NATURAL_QUERY, settings=settings))
    except Nl2SparqlError as error:
        logging.getLogger(__name__).error("command_failed error=%s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
