"""Fake OpenAI and SPARQL clients shared by the test modules. No network access."""

import json
from types import SimpleNamespace
from unittest import mock

from rdflib import Graph

SIMPLE_QUERY = "SELECT ?name WHERE { ?person foaf:name ?name } LIMIT 5"


def make_openai_client(reply_text=None, error=None, choices=None):
    """Build a fake OpenAI client that returns one canned reply."""
    if choices is None:
        choices = [SimpleNamespace(message=SimpleNamespace(content=reply_text))]
    create = mock.Mock(return_value=SimpleNamespace(choices=choices), side_effect=error)
    completions = SimpleNamespace(create=create)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def encode_fake_response(response):
    """Return (body bytes, content type) the way an endpoint would send the response."""
    if isinstance(response, Graph):
        return response.serialize(format="turtle").encode("utf-8"), "text/turtle"
    if isinstance(response, bytes):
        return response, "application/sparql-results+json"
    return json.dumps(response).encode("utf-8"), "application/sparql-results+json"


def make_sparql_client(response=None, error=None, content_type=None):
    """Build a fake SPARQLWrapper client that serves one raw response."""
    body, default_content_type = encode_fake_response(response)
    if content_type is None:
        content_type = default_content_type
    http_response = mock.Mock()
    http_response.read.return_value = body
    result = SimpleNamespace(
        info=mock.Mock(return_value={"content-type": content_type}),
        response=http_response,
    )
    return SimpleNamespace(
        query=mock.Mock(return_value=result, side_effect=error), http_response=http_response
    )


def make_bindings_response(rows):
    """Wrap rows in the SPARQL JSON results format."""
    bindings = [
        {name: {"type": "literal", "value": value} for name, value in row.items()}
        for row in rows
    ]
    return {"results": {"bindings": bindings}}
