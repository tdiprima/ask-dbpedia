"""Tests that run the real SPARQLWrapper and OpenAI client setup over a fake HTTP transport.

Nothing here touches the network: SPARQLWrapper's urlopen is replaced, and
every other loader is intercepted to prove no secondary request is made.
"""

import contextlib
import io
import json
import os
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from nl2sparql.errors import ConfigurationError, QueryExecutionError
from nl2sparql.sparql_executor import USER_AGENT, execute_sparql
from tests.fakes import SIMPLE_QUERY, make_bindings_response, make_openai_client
from nl2sparql.openai_backend import create_openai_client, generate_sparql

CONSTRUCT_QUERY = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 2"
TEST_ENDPOINT = "https://sparql.example.test/endpoint"
TEST_TIMEOUT_SECONDS = 7
TEST_ENVIRONMENT = {
    "DBPEDIA_ENDPOINT": TEST_ENDPOINT,
    "REQUEST_TIMEOUT_SECONDS": str(TEST_TIMEOUT_SECONDS),
}

JSON_CONTENT_TYPE = "application/sparql-results+json"
TURTLE_BODY = """
@prefix dbr: <http://dbpedia.org/resource/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
dbr:Rudolf_Virchow rdfs:label "Rudolf Virchow"@en ;
    rdfs:comment "Pathologe für Zellen" .
""".encode("utf-8")
EXPECTED_TURTLE_ROWS = [
    {
        "subject": "http://dbpedia.org/resource/Rudolf_Virchow",
        "predicate": "http://www.w3.org/2000/01/rdf-schema#comment",
        "object": "Pathologe für Zellen",
    },
    {
        "subject": "http://dbpedia.org/resource/Rudolf_Virchow",
        "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
        "object": "Rudolf Virchow",
    },
]
LOOPBACK_CONTEXT_URL = "http://127.0.0.1:9876/internal-context.jsonld"
JSON_LD_BODY = json.dumps(
    {"@context": LOOPBACK_CONTEXT_URL, "@id": "http://x/s", "name": "Virchow"}
).encode("utf-8")

# Every way a parser could load a secondary resource.
SECONDARY_LOADERS = (
    "rdflib.plugins.shared.jsonld.context.source_to_json",
    "rdflib.parser.URLInputSource",
    "urllib.request.OpenerDirector.open",
    "socket.create_connection",
    "builtins.open",
)


class FakeHttpResponse:
    """Stands in for the http.client.HTTPResponse that urlopen returns."""

    def __init__(self, body, content_type):
        self.body = body
        self.content_type = content_type
        self.is_closed = False

    def info(self):
        return {"Content-Type": self.content_type}

    def read(self, amount=-1):
        if amount < 0:
            return self.body
        return self.body[:amount]

    def close(self):
        self.is_closed = True


class TransportTestCase(unittest.TestCase):
    def run_query(self, sparql_query, body, content_type, error=None):
        """Execute through the real client. Return (rows, urlopen mock, loader mocks)."""
        http_response = FakeHttpResponse(body, content_type)
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, TEST_ENVIRONMENT))
            urlopen = stack.enter_context(
                mock.patch(
                    "SPARQLWrapper.Wrapper.urlopener",
                    return_value=http_response,
                    side_effect=error,
                )
            )
            loaders = [stack.enter_context(mock.patch(name)) for name in SECONDARY_LOADERS]
            self.last_urlopen = urlopen
            self.last_loaders = loaders
            self.last_http_response = http_response
            rows = execute_sparql(sparql_query)
        return rows

    def assert_no_secondary_requests(self):
        self.assertEqual(self.last_urlopen.call_count, 1)
        for loader in self.last_loaders:
            loader.assert_not_called()


class ResponseSecurityBoundaryTests(TransportTestCase):
    def test_response_cannot_fetch_external_context(self):
        hostile_content_types = ("application/ld+json", "application/ld+json; charset=utf-8")
        for sparql_query in (SIMPLE_QUERY, CONSTRUCT_QUERY, "DESCRIBE dbr:Paris"):
            for content_type in hostile_content_types:
                with self.subTest(sparql_query=sparql_query, content_type=content_type):
                    with self.assertRaises(QueryExecutionError):
                        self.run_query(sparql_query, JSON_LD_BODY, content_type)
                    self.assert_no_secondary_requests()
                    self.assertTrue(self.last_http_response.is_closed)

    def test_json_ld_labelled_as_an_accepted_type_still_fetches_nothing(self):
        disguises = ((SIMPLE_QUERY, JSON_CONTENT_TYPE), (CONSTRUCT_QUERY, "text/turtle"))
        for sparql_query, content_type in disguises:
            with self.subTest(content_type=content_type):
                with self.assertRaises(QueryExecutionError):
                    self.run_query(sparql_query, JSON_LD_BODY, content_type)
                self.assert_no_secondary_requests()

    def test_other_parsers_that_can_resolve_resources_are_refused(self):
        rdf_xml = (
            b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
            b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">&x;</rdf:RDF>'
        )
        for content_type in ("application/rdf+xml", "application/xml", "text/html", "text/n3"):
            with self.subTest(content_type=content_type):
                with self.assertRaises(QueryExecutionError):
                    self.run_query(CONSTRUCT_QUERY, rdf_xml, content_type)
                self.assert_no_secondary_requests()

    def test_valid_responses_pass_with_the_same_interceptors(self):
        rows = [{"name": "Rudolf Virchow"}]
        json_body = json.dumps(make_bindings_response(rows)).encode("utf-8")
        self.assertEqual(self.run_query(SIMPLE_QUERY, json_body, JSON_CONTENT_TYPE), rows)
        self.assert_no_secondary_requests()
        self.assertEqual(
            self.run_query(CONSTRUCT_QUERY, TURTLE_BODY, "text/turtle; charset=UTF-8"),
            EXPECTED_TURTLE_ROWS,
        )
        self.assert_no_secondary_requests()


class SparqlClientConfigurationTests(TransportTestCase):
    def sent_request(self):
        return self.last_urlopen.call_args.args[0]

    def sent_query_parameters(self):
        return parse_qs(urlparse(self.sent_request().full_url).query)

    def test_select_sends_the_query_endpoint_timeout_and_json_accept(self):
        json_body = json.dumps(make_bindings_response([{"name": "A"}])).encode("utf-8")
        self.run_query(f"  {SIMPLE_QUERY}\n", json_body, JSON_CONTENT_TYPE)
        request = self.sent_request()
        self.assertTrue(request.full_url.startswith(f"{TEST_ENDPOINT}?"))
        self.assertEqual(self.sent_query_parameters()["query"], [SIMPLE_QUERY])
        self.assertEqual(self.last_urlopen.call_args.kwargs, {"timeout": TEST_TIMEOUT_SECONDS})
        self.assertEqual(request.get_header("User-agent"), USER_AGENT)
        self.assertIn(JSON_CONTENT_TYPE, request.get_header("Accept"))
        self.assertNotIn("ld+json", request.get_header("Accept"))
        self.assertEqual(request.get_method(), "GET")

    def test_construct_asks_for_turtle_not_xml_or_json_ld(self):
        self.run_query(CONSTRUCT_QUERY, TURTLE_BODY, "text/turtle")
        accept_header = self.sent_request().get_header("Accept")
        self.assertIn("text/turtle", accept_header)
        self.assertNotIn("xml", accept_header)
        self.assertNotIn("ld+json", accept_header)
        self.assertEqual(self.sent_query_parameters()["query"], [CONSTRUCT_QUERY])

    def test_invalid_configuration_stops_before_any_request(self):
        bad_settings = ({"DBPEDIA_ENDPOINT": "file:///etc/passwd"}, {"REQUEST_TIMEOUT_SECONDS": "0"})
        for bad_setting in bad_settings:
            with self.subTest(bad_setting=bad_setting):
                with mock.patch.dict(TEST_ENVIRONMENT, bad_setting):
                    with self.assertRaises(ConfigurationError):
                        self.run_query(SIMPLE_QUERY, b"{}", JSON_CONTENT_TYPE)
                self.last_urlopen.assert_not_called()


class ResponseConversionTests(TransportTestCase):
    def test_select_body_is_decoded_into_rows(self):
        rows = [{"name": "Rudolf Virchow", "note": "Zellularpathologie für 病理学"}, {"name": "A"}]
        json_body = json.dumps(make_bindings_response(rows)).encode("utf-8")
        self.assertEqual(self.run_query(SIMPLE_QUERY, json_body, JSON_CONTENT_TYPE), rows)

    def test_construct_body_is_decoded_into_sorted_triple_rows(self):
        self.assertEqual(
            self.run_query(CONSTRUCT_QUERY, TURTLE_BODY, "text/turtle"), EXPECTED_TURTLE_ROWS
        )

    def test_empty_graph_body_gives_no_rows(self):
        self.assertEqual(self.run_query(CONSTRUCT_QUERY, b"# Empty TURTLE\n", "text/turtle"), [])

    def test_malformed_bodies_are_domain_errors(self):
        malformed = (
            (SIMPLE_QUERY, b"", JSON_CONTENT_TYPE),
            (SIMPLE_QUERY, b'{"results": {"bindings": [', JSON_CONTENT_TYPE),
            (SIMPLE_QUERY, b"<html>502 Bad Gateway</html>", JSON_CONTENT_TYPE),
            (SIMPLE_QUERY, b"\xff\xfe\x00bad", JSON_CONTENT_TYPE),
            (CONSTRUCT_QUERY, b"<http://x/s> <http://x/p> .", "text/turtle"),
            (CONSTRUCT_QUERY, b"<http://x/s> <http://x/p> \"unclosed", "text/turtle"),
            (CONSTRUCT_QUERY, b"<rdf:RDF></rdf:RDF>", "text/turtle"),
            (CONSTRUCT_QUERY, b"\xff\xfe\x00bad", "text/turtle"),
        )
        for sparql_query, body, content_type in malformed:
            with self.subTest(body=body):
                with self.assertRaises(QueryExecutionError):
                    self.run_query(sparql_query, body, content_type)
                self.assertTrue(self.last_http_response.is_closed)

    def test_http_errors_are_domain_errors(self):
        for status in (400, 401, 403, 404, 500, 503):
            with self.subTest(status=status):
                error = HTTPError(TEST_ENDPOINT, status, "failed", {}, io.BytesIO(b"details"))
                with self.assertLogs("nl2sparql.sparql_executor", level="ERROR"):
                    with self.assertRaises(QueryExecutionError):
                        self.run_query(SIMPLE_QUERY, b"", JSON_CONTENT_TYPE, error=error)


class OpenAiClientConfigurationTests(unittest.TestCase):
    DUMMY_API_KEY = "dummy-key-for-tests"

    def test_constructor_receives_the_key_and_timeout(self):
        environment = {"OPENAI_API_KEY": f"  {self.DUMMY_API_KEY}  ", "REQUEST_TIMEOUT_SECONDS": "7"}
        with mock.patch.dict(os.environ, environment):
            client = create_openai_client()
        self.assertEqual(client.api_key, self.DUMMY_API_KEY)
        self.assertEqual(client.timeout, 7)

    def test_missing_or_blank_key_never_builds_a_client(self):
        for blank_key in ("", "   "):
            with self.subTest(blank_key=blank_key):
                with mock.patch.dict(os.environ, {"OPENAI_API_KEY": blank_key}):
                    with mock.patch("nl2sparql.openai_backend.openai.OpenAI") as constructor:
                        with self.assertRaises(ConfigurationError):
                            create_openai_client()
                    constructor.assert_not_called()

    def test_bad_timeout_never_builds_a_client(self):
        environment = {"OPENAI_API_KEY": self.DUMMY_API_KEY, "REQUEST_TIMEOUT_SECONDS": "abc"}
        with mock.patch.dict(os.environ, environment):
            with self.assertRaises(ConfigurationError):
                create_openai_client()

    def test_configured_and_default_model_reach_the_api(self):
        for environment, expected_model in (({"OPENAI_MODEL": "test-model"}, "test-model"), ({"OPENAI_MODEL": ""}, "gpt-5.2")):
            with self.subTest(expected_model=expected_model):
                client = make_openai_client(SIMPLE_QUERY)
                with mock.patch.dict(os.environ, environment):
                    generate_sparql("Name some people", client)
                sent_model = client.chat.completions.create.call_args.kwargs["model"]
                self.assertEqual(sent_model, expected_model)


if __name__ == "__main__":
    unittest.main()
