"""Tokenize SPARQL text and find the boundaries of a complete read-only query.

Pure text logic. No network access. This is a boundary scanner, not a full
SPARQL parser: text inside { } groups is only checked for balanced braces.
"""

import re
from collections import namedtuple

Token = namedtuple("Token", ["kind", "text", "start", "end"])

READ_ONLY_QUERY_FORMS = ("SELECT", "ASK", "DESCRIBE", "CONSTRUCT")
GRAPH_QUERY_FORMS = ("DESCRIBE", "CONSTRUCT")
DECLARATION_KEYWORDS = ("PREFIX", "BASE")
# SERVICE makes the endpoint send requests to another server of the query's choosing.
FORBIDDEN_KEYWORDS = ("SERVICE",)

# Words that may appear outside the { } groups of a query.
OUTER_KEYWORDS = frozenset(
    (
        "DISTINCT", "REDUCED", "AS", "FROM", "NAMED", "WHERE",
        "GROUP", "BY", "HAVING", "ORDER", "ASC", "DESC",
        "LIMIT", "OFFSET", "VALUES", "UNDEF",
    )
)
OUTER_SYMBOLS = frozenset("()*,<>=!+-/|&")
ALWAYS_OUTER_KINDS = frozenset(("variable", "number", "string", "iri"))
IGNORED_KINDS = frozenset(("space", "comment"))

# Strings and IRIs come before comments so a '#' inside them is not a comment.
TOKEN_PATTERN = re.compile(
    r"""
      (?P<space>\s+)
    | (?P<string>\"\"\"(?:[^\\]|\\.)*?\"\"\"
               | '''(?:[^\\]|\\.)*?'''
               | "(?:[^"\\\n]|\\.)*"
               | '(?:[^'\\\n]|\\.)*')
    | (?P<iri><[^<>"{}|^`\\\s]*>)
    | (?P<comment>\#[^\n]*)
    | (?P<open>\{)
    | (?P<close>\})
    | (?P<variable>[?$]\w+)
    | (?P<number>\d+(?:\.\d+)?)
    | (?P<name>(?:[A-Za-z_][\w-]*)?:[\w-]* | [A-Za-z_][\w-]*)
    | (?P<other>.)
    """,
    re.VERBOSE | re.DOTALL,
)


def tokenize(text):
    """Return the tokens of the text, without whitespace and comments."""
    tokens = []
    for match in TOKEN_PATTERN.finditer(text):
        if match.lastgroup in IGNORED_KINDS:
            continue
        tokens.append(Token(match.lastgroup, match.group(), match.start(), match.end()))
    return tokens


def is_keyword(token, keywords):
    return token.kind == "name" and token.text.upper() in keywords


def declaration_length(tokens, index):
    """Return how many tokens form one PREFIX/BASE declaration at index, or 0."""
    following_kinds = [token.kind for token in tokens[index + 1:index + 3]]
    if is_keyword(tokens[index], ("BASE",)) and following_kinds[:1] == ["iri"]:
        return 2
    if not is_keyword(tokens[index], ("PREFIX",)):
        return 0
    if following_kinds != ["name", "iri"]:
        return 0
    if not tokens[index + 1].text.endswith(":"):
        return 0
    return 3


def skip_declarations(tokens, index):
    """Return the index of the first token after any PREFIX/BASE declarations."""
    while index < len(tokens):
        length = declaration_length(tokens, index)
        if length == 0:
            break
        index += length
    return index


def find_query_form(sparql_query):
    """Return the upper-case query form that follows any PREFIX/BASE lines."""
    tokens = tokenize(sparql_query)
    index = skip_declarations(tokens, 0)
    if index >= len(tokens) or tokens[index].kind != "name":
        return ""
    return tokens[index].text.upper()


def find_forbidden_keyword(sparql_query):
    """Return the first forbidden keyword used anywhere in the query, or "".

    Strings, IRIs, comments, variables, and prefixed names are separate
    tokens, so a harmless "service" inside them does not match.
    """
    for token in tokenize(sparql_query):
        if is_keyword(token, FORBIDDEN_KEYWORDS):
            return token.text.upper()
    return ""


def find_group_end(tokens, open_index):
    """Return the index of the '}' that closes the '{' at open_index, or None."""
    depth = 0
    for index in range(open_index, len(tokens)):
        if tokens[index].kind == "open":
            depth += 1
        if tokens[index].kind == "close":
            depth -= 1
        if depth == 0:
            return index
    return None


def is_outer_token(tokens, index):
    """True when the token may appear outside the { } groups of a query."""
    token = tokens[index]
    if token.kind in ALWAYS_OUTER_KINDS:
        return True
    if token.kind == "other":
        return token.text in OUTER_SYMBOLS
    if token.kind != "name":
        return False
    # A prefix with no local part ("Note:") is far more likely prose than SPARQL.
    is_prefixed_name = ":" in token.text and not token.text.endswith(":")
    if is_prefixed_name or token.text.upper() in OUTER_KEYWORDS:
        return True
    is_function_call = index + 1 < len(tokens) and tokens[index + 1].text == "("
    return is_function_call


def scan_query_body(tokens, index):
    """Walk the tokens after the query form.

    Return (index after the last query token, number of { } groups),
    or None when a { } group is never closed.
    """
    group_count = 0
    while index < len(tokens):
        if tokens[index].kind == "open":
            group_end = find_group_end(tokens, index)
            if group_end is None:
                return None
            group_count += 1
            index = group_end + 1
        elif is_outer_token(tokens, index):
            index += 1
        else:
            break
    return index, group_count


def find_query_end(tokens, start_index):
    """Return the index after the last token of the query at start_index, or None."""
    form_index = skip_declarations(tokens, start_index)
    if form_index >= len(tokens):
        return None
    if not is_keyword(tokens[form_index], READ_ONLY_QUERY_FORMS):
        return None
    body = scan_query_body(tokens, form_index + 1)
    if body is None:
        return None
    end_index, group_count = body
    is_describe = tokens[form_index].text.upper() == "DESCRIBE"
    has_body = end_index > form_index + 1
    if group_count == 0 and not (is_describe and has_body):
        return None
    return end_index


def find_complete_queries(text):
    """Return every complete read-only query inside the text.

    Prose before, between, and after the queries is left out.
    """
    tokens = tokenize(text)
    start_keywords = DECLARATION_KEYWORDS + READ_ONLY_QUERY_FORMS
    queries = []
    index = 0
    while index < len(tokens):
        end_index = None
        if is_keyword(tokens[index], start_keywords):
            end_index = find_query_end(tokens, index)
        if end_index is None:
            index += 1
            continue
        queries.append(text[tokens[index].start:tokens[end_index - 1].end])
        index = end_index
    return queries
