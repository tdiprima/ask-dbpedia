"""Run the five pre-defined pathology-related SPARQL queries on DBPedia."""

import logging
import sys

from nl2sparql.display import display_results, write_line
from nl2sparql.config import load_settings
from nl2sparql.errors import Nl2SparqlError
from nl2sparql.sparql_executor import execute_query
from nl2sparql.logging_setup import configure_logging
from nl2sparql.pathology_queries import PATHOLOGY_QUERIES

logger = logging.getLogger(__name__)


def run_titled_query(title, sparql_query, *, settings=None):
    """Run one query and display it. Return True on success."""
    write_line(f"\n=== {title} ===")
    try:
        display_results(execute_query(sparql_query, settings=settings))
    except Nl2SparqlError as error:
        logger.error("pathology_query_failed title=%s error=%s", title, error)
        return False
    return True


def main():
    try:
        settings = load_settings()
        configure_logging(settings.log_level)
    except Nl2SparqlError as error:
        logger.error("configuration_failed error=%s", error)
        return 1
    outcomes = [
        run_titled_query(title, sparql_query, settings=settings)
        for title, sparql_query in PATHOLOGY_QUERIES.items()
    ]
    if not all(outcomes):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
