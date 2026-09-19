"""Run a single pathology-related SPARQL query on DBPedia."""

import sys
import logging

from config import load_settings
from errors import Nl2SparqlError
from logging_setup import configure_logging
from pathology_queries import PATHOLOGY_SCIENTISTS
from cli_pathology_batch import run_titled_query


def main():
    try:
        settings = load_settings()
        configure_logging(settings.log_level)
    except Nl2SparqlError as error:
        logging.getLogger(__name__).error("configuration_failed error=%s", error)
        return 1
    if not run_titled_query("Pathology scientists", PATHOLOGY_SCIENTISTS, settings=settings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
