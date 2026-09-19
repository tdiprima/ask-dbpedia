"""Run a single pathology-related SPARQL query on DBPedia."""

import sys

from logging_setup import configure_logging
from pathology_queries import PATHOLOGY_SCIENTISTS
from run_pathology_queries import run_titled_query


def main():
    configure_logging()
    if not run_titled_query("Pathology scientists", PATHOLOGY_SCIENTISTS):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
