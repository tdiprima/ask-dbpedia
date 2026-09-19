"""Run the five pre-defined pathology-related SPARQL queries on DBPedia."""

import logging
import sys

from display import display_results, write_line
from errors import Nl2SparqlError
from executor import execute_sparql
from logging_setup import configure_logging
from pathology_queries import PATHOLOGY_QUERIES

logger = logging.getLogger(__name__)


def run_titled_query(title, sparql_query):
    """Run one query and display it. Return True on success."""
    write_line(f"\n=== {title} ===")
    try:
        display_results(execute_sparql(sparql_query))
    except Nl2SparqlError as error:
        logger.error("pathology_query_failed title=%s error=%s", title, error)
        return False
    return True


def main():
    configure_logging()
    outcomes = [
        run_titled_query(title, sparql_query)
        for title, sparql_query in PATHOLOGY_QUERIES.items()
    ]
    if not all(outcomes):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
