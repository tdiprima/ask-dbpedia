"""Run a SPARQL query against DBPedia and return the result rows."""

import logging
import sys
from http.client import HTTPException
from urllib.error import URLError

from SPARQLWrapper import JSON, TURTLE, SPARQLWrapper
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from config import get_dbpedia_endpoint, get_request_timeout_seconds
from display import display_results
from errors import Nl2SparqlError, QueryExecutionError
from logging_setup import configure_logging
from sparql_response import parse_response
from sparql_scanner import GRAPH_QUERY_FORMS, find_query_form
from sparql_text import validate_sparql_query

logger = logging.getLogger(__name__)

USER_AGENT = "nl2sparql/1.0 (https://github.com/tdiprima/nl2sparql)"

MAX_RESPONSE_BYTES = 10 * 1024 * 1024

EXAMPLE_SPARQL_QUERY = """
SELECT ?name WHERE {
    ?person a dbo:Scientist .
    ?person dbo:award dbr:Nobel_Prize_in_Physics .
    ?person foaf:name ?name .
} LIMIT 10
"""


def choose_return_format(sparql_query):
    """CONSTRUCT and DESCRIBE return an RDF graph. SELECT and ASK return JSON."""
    # Turtle, because its parser never fetches external resources. RDF/XML and JSON-LD can.
    if find_query_form(sparql_query) in GRAPH_QUERY_FORMS:
        return TURTLE
    return JSON


def create_sparql_client(sparql_query):
    """Build a SPARQLWrapper configured for one query."""
    client = SPARQLWrapper(get_dbpedia_endpoint(), agent=USER_AGENT)
    client.setTimeout(get_request_timeout_seconds())
    client.setReturnFormat(choose_return_format(sparql_query))
    client.setQuery(sparql_query)
    return client


def fetch_response(client):
    """Send the query. Return the content type header and the raw, unparsed body.

    SPARQLWrapper's own convert() is not used: it picks a parser from the
    response content type, so a hostile endpoint could select one that
    fetches external resources (JSON-LD @context).
    """
    result = client.query()
    try:
        content_type_header = result.info().get("content-type", "")
        body = result.response.read(MAX_RESPONSE_BYTES + 1)
    finally:
        result.response.close()
    if len(body) > MAX_RESPONSE_BYTES:
        raise QueryExecutionError(f"SPARQL response exceeds {MAX_RESPONSE_BYTES} bytes")
    return content_type_header, body


def execute_sparql(sparql_query, client=None):
    """Run a read-only SPARQL query and return a list of result rows."""
    valid_query = validate_sparql_query(sparql_query)
    if client is None:
        client = create_sparql_client(valid_query)
    try:
        content_type_header, body = fetch_response(client)
    except (
        SPARQLWrapperException,
        URLError,
        TimeoutError,
        HTTPException,
        ValueError,
    ) as error:
        logger.error("sparql_execution_failed error=%s", error)
        raise QueryExecutionError(f"SPARQL execution failed: {error}") from error
    results = parse_response(find_query_form(valid_query), content_type_header, body)
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
