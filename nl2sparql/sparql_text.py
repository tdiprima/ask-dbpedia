"""Pure text helpers: prompt building and SPARQL cleanup. No network access."""

import re

from nl2sparql.errors import InvalidInputError, QueryGenerationError
from nl2sparql.sparql_scanner import find_complete_queries
from nl2sparql.sparql_policy import validate_sparql_query, MAX_SPARQL_QUERY_LENGTH


MAX_NATURAL_QUERY_LENGTH = 1000
MAX_MODEL_REPLY_LENGTH = 50000

SYSTEM_PROMPT = (
    "You translate natural language questions into SPARQL queries for DBPedia. "
    "Use the standard DBPedia prefixes (dbo:, dbr:, dbp:, foaf:, rdfs:). "
    "Always begin the query with the PREFIX declarations for every prefix you use. "
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


def extract_sparql(model_reply):
    """Pull the SPARQL query out of a language model reply."""
    if not isinstance(model_reply, str) or not model_reply.strip():
        raise QueryGenerationError("Language model returned an empty reply")
    if len(model_reply) > MAX_MODEL_REPLY_LENGTH:
        raise QueryGenerationError(
            f"Language model reply exceeds {MAX_MODEL_REPLY_LENGTH} characters"
        )
    candidates = CODE_FENCE_PATTERN.findall(model_reply) or [model_reply]
    complete_queries = [query for text in candidates for query in find_complete_queries(text)]
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
