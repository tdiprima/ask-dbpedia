"""Turn the raw body of a SPARQL endpoint response into a list of rows.

Pure parsing. No network access. The response is untrusted: only the content
types we asked for are parsed, and only with parsers that never fetch
external resources (JSON-LD and RDF/XML can, so they are refused).
"""

import json

from rdflib import Graph
from rdflib.plugins.parsers.notation3 import BadSyntax

from errors import QueryExecutionError
from sparql_scanner import GRAPH_QUERY_FORMS

JSON_CONTENT_TYPES = ("application/sparql-results+json", "application/json")
GRAPH_CONTENT_TYPES = ("text/turtle", "application/x-turtle", "application/n-triples")


def normalize_content_type(content_type_header):
    """Return the lower-case media type without parameters such as charset."""
    if not isinstance(content_type_header, str):
        return ""
    return content_type_header.split(";")[0].strip().lower()


def check_content_type(content_type, allowed_content_types):
    """Refuse a response whose content type we did not ask for."""
    if content_type not in allowed_content_types:
        raise QueryExecutionError(
            f"SPARQL endpoint returned content type {content_type!r}, "
            f"expected one of {', '.join(allowed_content_types)}"
        )


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


def parse_json_body(body):
    """Parse a SPARQL JSON results body."""
    try:
        return json.loads(body)
    except ValueError as error:
        raise QueryExecutionError(f"SPARQL response is not valid JSON: {error}") from error


def parse_turtle_body(body):
    """Parse a Turtle or N-Triples body. The Turtle parser never fetches anything."""
    graph = Graph()
    try:
        graph.parse(data=body, format="turtle")
    except (BadSyntax, ValueError) as error:
        raise QueryExecutionError(f"SPARQL response is not valid Turtle: {error}") from error
    return graph


def parse_response(query_form, content_type_header, body):
    """Check the content type for this query form, then parse the body into rows."""
    content_type = normalize_content_type(content_type_header)
    if query_form in GRAPH_QUERY_FORMS:
        check_content_type(content_type, GRAPH_CONTENT_TYPES)
        return flatten_response(parse_turtle_body(body))
    check_content_type(content_type, JSON_CONTENT_TYPES)
    return flatten_response(parse_json_body(body))
