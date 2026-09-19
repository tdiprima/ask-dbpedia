"""Run a SPARQL query against DBPedia and return the result rows."""

import logging
from http.client import HTTPException
from urllib.error import URLError

from SPARQLWrapper import JSON, TURTLE, SPARQLWrapper
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from config import load_settings
from errors import QueryExecutionError
from sparql_response import parse_result
from sparql_policy import GRAPH_QUERY_FORMS, find_query_form, validate_sparql_query

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


def create_sparql_client(sparql_query, *, settings=None):
    """Build a SPARQLWrapper configured for one query."""
    settings = settings or load_settings()
    client = SPARQLWrapper(settings.endpoint, agent=USER_AGENT)
    client.setTimeout(settings.timeout)
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


def execute_query(sparql_query, client=None, *, settings=None):
    """Run a read-only query and return typed values in a QueryResult."""
    valid_query = validate_sparql_query(sparql_query)
    if client is None:
        client = create_sparql_client(valid_query, settings=settings)
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
    results = parse_result(find_query_form(valid_query), content_type_header, body)
    logger.info("sparql_executed rows=%d", len(results.rows))
    return results


def execute_sparql(sparql_query, client=None, *, settings=None):
    """Compatibility API returning string rows; execute_query preserves RDF types."""
    return execute_query(sparql_query, client, settings=settings).text_rows()
