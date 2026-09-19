"""Shared pipeline: natural language -> SPARQL -> DBPedia -> validated output."""

import logging

from display import display_results, write_line
from errors import Nl2SparqlError
from executor import execute_sparql
from logging_setup import configure_logging
from validator import validate_results

logger = logging.getLogger(__name__)


def run_pipeline(natural_query, generate_sparql):
    """Generate, execute, and validate. Return the query, the rows, and a validity flag."""
    sparql_query = generate_sparql(natural_query)
    results = execute_sparql(sparql_query)
    return sparql_query, results, validate_results(results)


def run_pipeline_cli(natural_query, generate_sparql):
    """Run the pipeline for a script and return a process exit code."""
    configure_logging()
    try:
        sparql_query, results, is_valid = run_pipeline(natural_query, generate_sparql)
    except Nl2SparqlError as error:
        logger.error("pipeline_failed error=%s", error)
        return 1
    write_line(f"Generated SPARQL query:\n{sparql_query}\n")
    display_results(results)
    if not is_valid:
        logger.warning("pipeline_results_not_meaningful")
        return 2
    return 0
