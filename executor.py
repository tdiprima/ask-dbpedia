"""Run a SPARQL query against DBPedia and return the result rows."""

import logging
import sys
from urllib.error import URLError

# Only the exception class is used, to catch RDF/XML parse failures. Nothing is parsed here.
from xml.sax import SAXException  # nosec B406

from rdflib import Graph
from SPARQLWrapper import JSON, RDFXML, SPARQLWrapper
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from config import get_dbpedia_endpoint, get_request_timeout_seconds
from display import display_results
from errors import Nl2SparqlError, QueryExecutionError
from logging_setup import configure_logging
from sparql_scanner import GRAPH_QUERY_FORMS, find_query_form
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


def choose_return_format(sparql_query):
    """CONSTRUCT and DESCRIBE return an RDF graph. SELECT and ASK return JSON."""
    if find_query_form(sparql_query) in GRAPH_QUERY_FORMS:
        return RDFXML
    return JSON


def create_sparql_client(sparql_query):
    """Build a SPARQLWrapper configured for one query."""
    client = SPARQLWrapper(get_dbpedia_endpoint(), agent=USER_AGENT)
    client.setTimeout(get_request_timeout_seconds())
    client.setReturnFormat(choose_return_format(sparql_query))
    client.setQuery(sparql_query)
    return client


def flatten_graph(graph):
    """Convert an RDF graph into a sorted list of subject/predicate/object rows."""
    # A graph is an unordered set. Sort so the same result always prints the same way.
    triples = sorted(tuple(str(term) for term in triple) for triple in graph)
    return [
        {"subject": subject, "predicate": predicate, "object": rdf_object}
        for subject, predicate, rdf_object in triples
    ]


def flatten_binding(binding):
    """Convert one SPARQL JSON binding into a {variable: value} row."""
    if not isinstance(binding, dict):
        raise QueryExecutionError("SPARQL response has a binding that is not an object")
    row = {}
    for name, cell in binding.items():
        if not isinstance(cell, dict):
            raise QueryExecutionError(f"SPARQL response cell {name!r} is not an object")
        value = cell.get("value", "")
        if not isinstance(value, str):
            raise QueryExecutionError(f"SPARQL response cell {name!r} has a non-text value")
        row[name] = value
    return row


def flatten_response(response):
    """Convert a SPARQL JSON response or RDF graph into a list of rows."""
    if isinstance(response, Graph):
        return flatten_graph(response)
    if not isinstance(response, dict):
        raise QueryExecutionError("SPARQL endpoint returned an unsupported response")
    if "boolean" in response:
        return [{"boolean": str(response["boolean"])}]
    results = response.get("results")
    if not isinstance(results, dict):
        raise QueryExecutionError("SPARQL response has no results object")
    bindings = results.get("bindings")
    if not isinstance(bindings, list):
        raise QueryExecutionError("SPARQL response has no results.bindings list")
    return [flatten_binding(binding) for binding in bindings]


def execute_sparql(sparql_query, client=None):
    """Run a read-only SPARQL query and return a list of result rows."""
    valid_query = validate_sparql_query(sparql_query)
    if client is None:
        client = create_sparql_client(valid_query)
    try:
        response = client.queryAndConvert()
    except (
        SPARQLWrapperException,
        URLError,
        TimeoutError,
        ValueError,
        SAXException,
    ) as error:
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
