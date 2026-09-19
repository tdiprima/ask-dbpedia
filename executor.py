"""Run a SPARQL query against DBPedia and return the result rows."""

import logging
import sys
from urllib.error import URLError

from SPARQLWrapper import JSON, SPARQLWrapper
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from config import get_dbpedia_endpoint, get_request_timeout_seconds
from display import display_results
from errors import Nl2SparqlError, QueryExecutionError
from logging_setup import configure_logging
from sparql_text import validate_sparql_query

logger = logging.getLogger(__name__)

USER_AGENT = "nl2sparql/1.0 (https://github.com/tdiprima/nl2sparql)"

EXAMPLE_SPARQL_QUERY = """
SELECT ?name WHERE {
    ?person a dbo:Scientist .
    ?person dbo:award dbr:Nobel_Prize_in_Physics .
    ?person foaf:name ?name .
} LIMIT 10
"""


def create_sparql_client(sparql_query):
    """Build a SPARQLWrapper configured for one JSON query."""
    client = SPARQLWrapper(get_dbpedia_endpoint(), agent=USER_AGENT)
    client.setTimeout(get_request_timeout_seconds())
    client.setReturnFormat(JSON)
    client.setQuery(sparql_query)
    return client


def flatten_response(response):
    """Convert a SPARQL JSON response into a list of {variable: value} rows."""
    if not isinstance(response, dict):
        raise QueryExecutionError("SPARQL endpoint returned a non-JSON response")
    if "boolean" in response:
        return [{"boolean": str(response["boolean"])}]
    bindings = response.get("results", {}).get("bindings")
    if bindings is None:
        raise QueryExecutionError("SPARQL response has no results.bindings")
    return [
        {name: cell.get("value", "") for name, cell in binding.items()}
        for binding in bindings
    ]


def execute_sparql(sparql_query, client=None):
    """Run a read-only SPARQL query and return a list of result rows."""
    valid_query = validate_sparql_query(sparql_query)
    if client is None:
        client = create_sparql_client(valid_query)
    try:
        response = client.queryAndConvert()
    except (SPARQLWrapperException, URLError, TimeoutError, ValueError) as error:
        logger.error("sparql_execution_failed error=%s", error)
        raise QueryExecutionError(f"SPARQL execution failed: {error}") from error
    results = flatten_response(response)
    logger.info("sparql_executed rows=%d", len(results))
    return results


def main():
    configure_logging()
    try:
        display_results(execute_sparql(EXAMPLE_SPARQL_QUERY))
    except Nl2SparqlError as error:
        logger.error("query_execution_failed error=%s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
