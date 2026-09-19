"""Turn the raw body of a SPARQL endpoint response into a list of rows.

Pure parsing. No network access. The response is untrusted: only the content
types we asked for are parsed, and only with parsers that never fetch
external resources (JSON-LD and RDF/XML can, so they are refused).
"""

import json

from rdflib import Graph, URIRef, BNode

from nl2sparql.results import QueryResult, Term

from nl2sparql.errors import QueryExecutionError
from nl2sparql.sparql_policy import GRAPH_QUERY_FORMS

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


def graph_term(term):
    if isinstance(term, URIRef):
        return Term(str(term), "uri")
    if isinstance(term, BNode):
        return Term(str(term), "bnode")
    return Term(str(term), "literal", str(term.datatype) if term.datatype else None, term.language)


def binding_term(cell):
    if not isinstance(cell, dict) or not isinstance(cell.get("value"), str):
        raise QueryExecutionError("SPARQL response cell must have a text value")
    kind = cell.get("type")
    if kind not in ("uri", "bnode", "literal", "typed-literal"):
        raise QueryExecutionError("SPARQL response cell has an invalid term type")
    datatype, language = cell.get("datatype"), cell.get("xml:lang")
    if any(value is not None and not isinstance(value, str) for value in (datatype, language)):
        raise QueryExecutionError("SPARQL term metadata must be text")
    return Term(cell["value"], "literal" if kind == "typed-literal" else kind, datatype, language)


def decode_result(response, form):
    """Preserve RDF term identity and ASK booleans at the transport boundary."""
    if isinstance(response, Graph):
        triples = sorted(response, key=lambda triple: (
            tuple(str(term) for term in triple),
            tuple(term.n3() for term in triple),
        ))
        return QueryResult(form, [
            dict(zip(("subject", "predicate", "object"), map(graph_term, triple)))
            for triple in triples
        ])
    if not isinstance(response, dict):
        raise QueryExecutionError("SPARQL endpoint returned an unsupported response")
    if "boolean" in response:
        if form != "ASK" or not isinstance(response["boolean"], bool):
            raise QueryExecutionError("SPARQL ASK response must contain a boolean")
        return QueryResult(form, [{"boolean": response["boolean"]}])
    if form == "ASK":
        raise QueryExecutionError("SPARQL ASK response has no boolean")
    results = response.get("results")
    if not isinstance(results, dict) or not isinstance(results.get("bindings"), list):
        raise QueryExecutionError("SPARQL response has no results.bindings list")
    rows = []
    for binding in results["bindings"]:
        if not isinstance(binding, dict):
            raise QueryExecutionError("SPARQL response binding must be an object")
        rows.append({name: binding_term(cell) for name, cell in binding.items()})
    return QueryResult(form, rows)


def flatten_response(response):
    """Compatibility view for callers that need the historical string rows."""
    form = "CONSTRUCT" if isinstance(response, Graph) else (
        "ASK" if isinstance(response, dict) and "boolean" in response else "SELECT"
    )
    return decode_result(response, form).text_rows()


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
    # Broad on purpose. On hostile input rdflib raises BadSyntax, AssertionError,
    # IndexError and others, so no specific list is safe. Nothing is swallowed:
    # every failure becomes a QueryExecutionError for the caller.
    except Exception as error:
        raise QueryExecutionError(f"SPARQL response is not valid Turtle: {error}") from error
    return graph


def parse_result(query_form, content_type_header, body):
    """Check the content type for this query form, then parse the body into rows."""
    content_type = normalize_content_type(content_type_header)
    if query_form in GRAPH_QUERY_FORMS:
        check_content_type(content_type, GRAPH_CONTENT_TYPES)
        return decode_result(parse_turtle_body(body), query_form)
    check_content_type(content_type, JSON_CONTENT_TYPES)
    return decode_result(parse_json_body(body), query_form)


def parse_response(query_form, content_type_header, body):
    """Compatibility view of a parsed response as string rows."""
    return parse_result(query_form, content_type_header, body).text_rows()
