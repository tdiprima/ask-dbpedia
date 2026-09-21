"""Validate complete SPARQL syntax and enforce the supported query policy.

Parsing never executes SPARQL or resolves resources. Undefined prefixes remain
permitted because DBpedia supplies its standard namespace bindings.
"""

from pyparsing import ParseBaseException, ParseResults
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue

from nl2sparql.errors import InvalidInputError

MAX_SPARQL_QUERY_LENGTH = 10000
READ_ONLY_QUERY_FORMS = ("SELECT", "ASK", "DESCRIBE", "CONSTRUCT")
GRAPH_QUERY_FORMS = ("DESCRIBE", "CONSTRUCT")


def parse_query(text):
    """Parse exactly one read-only query, rejecting incomplete or trailing syntax."""
    if not isinstance(text, str) or not text.strip():
        raise InvalidInputError("SPARQL query must be a non-empty string")
    if len(text.strip()) > MAX_SPARQL_QUERY_LENGTH:
        raise InvalidInputError(f"SPARQL query exceeds {MAX_SPARQL_QUERY_LENGTH} characters")
    try:
        return parseQuery(text.strip())
    except (ParseBaseException, ValueError, RecursionError) as error:
        raise InvalidInputError("Expected one syntactically valid read-only SPARQL query") from error


def find_query_form(text):
    return parse_query(text)[1].name.removesuffix("Query").upper()


def validate_sparql_query(text):
    """Validate syntax and reject federation anywhere in the parsed query."""
    parsed = parse_query(text)
    pending = [parsed]
    while pending:
        node = pending.pop()
        if isinstance(node, CompValue) and node.name == "ServiceGraphPattern":
            raise InvalidInputError("SERVICE is not allowed in queries")
        if isinstance(node, dict):
            pending.extend(node.values())
        elif isinstance(node, (list, tuple, ParseResults)):
            pending.extend(node)
    return text.strip()
