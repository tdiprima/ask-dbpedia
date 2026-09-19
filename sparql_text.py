"""Pure text helpers: prompt building and SPARQL cleanup. No network access."""

import re

from errors import InvalidInputError, QueryGenerationError
from sparql_scanner import READ_ONLY_QUERY_FORMS, find_complete_queries, find_query_form

MAX_NATURAL_QUERY_LENGTH = 1000
MAX_SPARQL_QUERY_LENGTH = 10000
MAX_MODEL_REPLY_LENGTH = 50000

SYSTEM_PROMPT = (
    "You translate natural language questions into SPARQL queries for DBPedia. "
    "Use the standard DBPedia prefixes (dbo:, dbr:, dbp:, foaf:, rdfs:). "
    "Always include a LIMIT clause. "
    "Reply with the SPARQL query only. No explanation. No markdown."
)

CODE_FENCE_PATTERN = re.compile(r"```(?:sparql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def validate_natural_query(natural_query):
    """Return the trimmed question, or raise InvalidInputError."""
    if not isinstance(natural_query, str):
        raise InvalidInputError("Natural language query must be a string")
    trimmed_query = natural_query.strip()
    if not trimmed_query:
        raise InvalidInputError("Natural language query must not be empty")
    if len(trimmed_query) > MAX_NATURAL_QUERY_LENGTH:
        raise InvalidInputError(
            f"Natural language query exceeds {MAX_NATURAL_QUERY_LENGTH} characters"
        )
    return trimmed_query


def build_chat_messages(natural_query):
    """Return the chat messages shared by every language model backend."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": validate_natural_query(natural_query)},
    ]


def validate_sparql_query(sparql_query):
    """Return the trimmed query. Only read-only query forms are accepted."""
    if not isinstance(sparql_query, str):
        raise InvalidInputError("SPARQL query must be a string")
    trimmed_query = sparql_query.strip()
    if not trimmed_query:
        raise InvalidInputError("SPARQL query must not be empty")
    if len(trimmed_query) > MAX_SPARQL_QUERY_LENGTH:
        raise InvalidInputError(
            f"SPARQL query exceeds {MAX_SPARQL_QUERY_LENGTH} characters"
        )
    query_form = find_query_form(trimmed_query)
    if query_form not in READ_ONLY_QUERY_FORMS:
        raise InvalidInputError(
            f"Only {', '.join(READ_ONLY_QUERY_FORMS)} queries are allowed, "
            f"got {query_form or 'nothing recognizable'!r}"
        )
    return trimmed_query


def extract_sparql(model_reply):
    """Pull the SPARQL query out of a language model reply."""
    if not isinstance(model_reply, str) or not model_reply.strip():
        raise QueryGenerationError("Language model returned an empty reply")
    if len(model_reply) > MAX_MODEL_REPLY_LENGTH:
        raise QueryGenerationError(
            f"Language model reply exceeds {MAX_MODEL_REPLY_LENGTH} characters"
        )
    candidate_text = model_reply
    fenced_block = CODE_FENCE_PATTERN.search(model_reply)
    if fenced_block:
        candidate_text = fenced_block.group(1)
    complete_queries = find_complete_queries(candidate_text)
    if not complete_queries:
        raise QueryGenerationError(
            "Language model reply contains no complete SPARQL query"
        )
    if len(complete_queries) > 1:
        raise QueryGenerationError(
            f"Language model reply contains {len(complete_queries)} SPARQL queries, expected one"
        )
    try:
        return validate_sparql_query(complete_queries[0])
    except InvalidInputError as error:
        raise QueryGenerationError(f"Generated SPARQL rejected: {error}") from error
