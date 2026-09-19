"""Check whether SPARQL query results are valid and meaningful."""

import logging

from results import QueryResult, Term

logger = logging.getLogger(__name__)


def is_meaningful_row(row):
    """A row is meaningful when it is a dict with at least one non-blank value."""
    if not isinstance(row, dict):
        return False
    return any(
        isinstance(value, bool)
        or isinstance(value, Term) and bool(value.value.strip())
        or isinstance(value, str) and bool(value.strip())
        for value in row.values()
    )


def validate_results(results):
    """Return True when results is a non-empty list of meaningful rows."""
    if isinstance(results, QueryResult):
        results = results.rows
    if not isinstance(results, list) or not results:
        logger.warning("results_invalid reason=empty_or_not_a_list")
        return False
    if not all(is_meaningful_row(row) for row in results):
        logger.warning("results_invalid reason=blank_or_malformed_row")
        return False
    return True
