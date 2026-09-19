"""Pure text helpers: prompt building and SPARQL cleanup. No network access."""

import re

from errors import InvalidInputError, QueryGenerationError

MAX_NATURAL_QUERY_LENGTH = 1000
MAX_SPARQL_QUERY_LENGTH = 10000

READ_ONLY_QUERY_FORMS = ("SELECT", "ASK", "DESCRIBE", "CONSTRUCT")

SYSTEM_PROMPT = (
    "You translate natural language questions into SPARQL queries for DBPedia. "
    "Use the standard DBPedia prefixes (dbo:, dbr:, dbp:, foaf:, rdfs:). "
    "Always include a LIMIT clause. "
    "Reply with the SPARQL query only. No explanation. No markdown."
)

CODE_FENCE_PATTERN = re.compile(r"```(?:sparql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
QUERY_START_PATTERN = re.compile(
    r"\b(PREFIX|BASE|SELECT|ASK|DESCRIBE|CONSTRUCT)\b", re.IGNORECASE
)
DECLARATION_PATTERN = re.compile(
    r"\s*(PREFIX\s+[^\s:]*:\s*<[^>]*>|BASE\s+<[^>]*>)", re.IGNORECASE
)
FIRST_WORD_PATTERN = re.compile(r"\s*([A-Za-z]+)")


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


def find_query_form(sparql_query):
    """Return the upper-case query form that follows any PREFIX/BASE lines."""
    remaining_text = sparql_query
    declaration = DECLARATION_PATTERN.match(remaining_text)
    while declaration:
        remaining_text = remaining_text[declaration.end():]
        declaration = DECLARATION_PATTERN.match(remaining_text)
    first_word = FIRST_WORD_PATTERN.match(remaining_text)
    if not first_word:
        return ""
    return first_word.group(1).upper()


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
    candidate_text = model_reply
    fenced_block = CODE_FENCE_PATTERN.search(model_reply)
    if fenced_block:
        candidate_text = fenced_block.group(1)
    query_start = QUERY_START_PATTERN.search(candidate_text)
    if not query_start:
        raise QueryGenerationError("Language model reply contains no SPARQL query")
    try:
        return validate_sparql_query(candidate_text[query_start.start():])
    except InvalidInputError as error:
        raise QueryGenerationError(f"Generated SPARQL rejected: {error}") from error
