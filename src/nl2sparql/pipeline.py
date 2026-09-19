"""Shared pipeline: natural language -> SPARQL -> DBPedia -> validated output."""

import logging

from display import display_results, write_line
from config import load_settings
from errors import Nl2SparqlError
from sparql_executor import execute_query
from logging_setup import configure_logging
from results import QueryResult
from validator import validate_results

logger = logging.getLogger(__name__)


def run_query_pipeline(natural_query, generate_sparql, *, settings=None, backend=None):
    """Return the generated query, typed result, and nonblank-result flag."""
    settings = settings or load_settings(backend)
    sparql_query = (
        generate_sparql(natural_query, settings=settings)
        if backend else generate_sparql(natural_query)
    )
    results = execute_query(sparql_query, settings=settings)
    return sparql_query, results, validate_results(results)


def run_pipeline(natural_query, generate_sparql, *, settings=None, backend=None):
    """Compatibility API returning the historical tuple with string rows."""
    query, results, valid = run_query_pipeline(
        natural_query, generate_sparql, settings=settings, backend=backend
    )
    rows = results.text_rows() if isinstance(results, QueryResult) else results
    return query, rows, valid


def run_pipeline_cli(natural_query, generate_sparql, *, backend=None):
    """Run the pipeline for a script and return a process exit code."""
    try:
        settings = load_settings(backend)
        configure_logging(settings.log_level)
        sparql_query, results, is_valid = run_query_pipeline(
            natural_query, generate_sparql, settings=settings, backend=backend
        )
    except Nl2SparqlError as error:
        logger.error("pipeline_failed error=%s", error)
        return 1
    write_line(f"Generated SPARQL query:\n{sparql_query}\n")
    display_results(results)
    if not is_valid:
        logger.warning("pipeline_results_not_meaningful")
        return 2
    return 0
