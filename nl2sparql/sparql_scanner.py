"""Locate query candidates; syntax and policy live in sparql_policy.py."""

import re
from collections import namedtuple

from pyparsing import Located, ParseBaseException
from rdflib.plugins.sparql.parser import Query

from nl2sparql.sparql_policy import READ_ONLY_QUERY_FORMS

Token = namedtuple("Token", ["kind", "text", "start", "end"])
DECLARATION_KEYWORDS = ("PREFIX", "BASE")
QUERY_CANDIDATE = Located(Query).parse_with_tabs()

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


def find_complete_queries(text):
    """Extract candidates using RDFLib's grammar, without executing any query.

    Tokenization only locates potential starts outside strings and comments.
    The parser determines each candidate's end; policy is checked separately.
    """
    queries = []
    consumed = 0
    for token in tokenize(text):
        if token.start < consumed or not is_keyword(token, DECLARATION_KEYWORDS + READ_ONLY_QUERY_FORMS):
            continue
        try:
            parsed = QUERY_CANDIDATE.parse_string(text[token.start:], parse_all=False)
        except (ParseBaseException, RecursionError):
            continue
        consumed = token.start + parsed.locn_end
        # Exclude trailing whitespace/comments consumed by the grammar.
        candidate_tokens = tokenize(text[token.start:consumed])
        end = token.start + candidate_tokens[-1].end
        queries.append(text[token.start:end])
    return queries
