"""Regression tests for syntax, typed results, startup, and existing launchers."""

import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from nl2sparql.config import load_settings
from nl2sparql.display import display_results
from nl2sparql.errors import ConfigurationError, InvalidInputError, QueryGenerationError
from nl2sparql.openai_backend import generate_sparql
from nl2sparql.pipeline import run_pipeline, run_query_pipeline, run_pipeline_cli
from nl2sparql.results import QueryResult, Term
from nl2sparql.sparql_executor import execute_query, execute_sparql
from nl2sparql.sparql_text import extract_sparql, validate_sparql_query
from tests.fakes import SIMPLE_QUERY, make_openai_client, make_sparql_client
from nl2sparql.validator import validate_results


class QuerySyntaxTests(unittest.TestCase):
    def test_valid_syntax_outside_braces_is_preserved(self):
        queries = (
            "SELECT ('bonjour'@fr AS ?label) WHERE {} LIMIT 1",
            "PREFIX ex: <http://example.org/> DESCRIBE ex:",
            "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> "
            "SELECT ('01'^^xsd:integer AS ?n) WHERE {}",
            "SELECT (1e3 AS ?n) WHERE {}",
            "SELECT ?s WHERE {\n\t?s ?p ?o\n} LIMIT 1",
        )
        for query in queries:
            with self.subTest(query=query):
                self.assertEqual(validate_sparql_query(query), query)
                self.assertEqual(extract_sparql(f"Query:\n{query}\nDone."), query)

    def test_whole_query_must_parse_before_transport(self):
        queries = (
            "SELECT ?s WHERE { ?s ?p }",
            "SELECT ?s WHERE { ?s ?p ?o } LIMIT banana",
            SIMPLE_QUERY + "; DROP ALL",
            SIMPLE_QUERY + " SELECT ?s WHERE { ?s ?p ?o }",
        )
        for query in queries:
            with self.subTest(query=query), mock.patch("nl2sparql.sparql_executor.fetch_response") as fetch:
                with self.assertRaises(InvalidInputError):
                    execute_query(query)
                fetch.assert_not_called()

    def test_nested_federation_is_rejected_but_literal_text_is_not(self):
        query = "SELECT ?s WHERE { { SELECT ?s WHERE { SERVICE SILENT ?url { ?s ?p ?o } } } }"
        with self.assertRaises(InvalidInputError):
            validate_sparql_query(query)
        harmless = 'SELECT ?s WHERE { ?s <http://x/service> "SERVICE" }'
        self.assertEqual(validate_sparql_query(harmless), harmless)

    def test_multiple_fenced_queries_are_ambiguous(self):
        reply = f"```sparql\n{SIMPLE_QUERY}\n```\n```sparql\nASK {{ ?s ?p ?o }}\n```"
        with self.assertRaises(QueryGenerationError):
            extract_sparql(reply)


class TypedResultTests(unittest.TestCase):
    def test_json_terms_keep_identity_datatype_and_language(self):
        cells = {
            "uri": {"type": "uri", "value": "http://x/s"},
            "literal": {"type": "literal", "value": "http://x/s"},
            "number": {"type": "literal", "value": "01", "datatype": "http://www.w3.org/2001/XMLSchema#integer"},
            "label": {"type": "literal", "value": "bonjour", "xml:lang": "fr"},
            "blank": {"type": "bnode", "value": "node1"},
        }
        result = execute_query(SIMPLE_QUERY, make_sparql_client({"results": {"bindings": [cells]}}))
        self.assertEqual(result.form, "SELECT")
        self.assertEqual(result.rows[0]["uri"], Term("http://x/s", "uri"))
        self.assertNotEqual(result.rows[0]["uri"], result.rows[0]["literal"])
        self.assertEqual(result.rows[0]["number"].value, "01")
        self.assertEqual(result.rows[0]["number"].datatype, cells["number"]["datatype"])
        self.assertEqual(result.rows[0]["label"].language, "fr")
        self.assertEqual(result.rows[0]["blank"].kind, "bnode")

    def test_graph_terms_keep_language_and_datatype(self):
        body = b'<http://x/s> <http://x/p> "same"@en, "same"@fr, "2"^^<http://www.w3.org/2001/XMLSchema#integer> .'
        result = execute_query("DESCRIBE <http://x/s>", make_sparql_client(body, content_type="text/turtle"))
        objects = [row["object"] for row in result.rows]
        self.assertIn(Term("same", "literal", language="en"), objects)
        self.assertIn(Term("same", "literal", language="fr"), objects)
        self.assertIn(Term("2", "literal", datatype="http://www.w3.org/2001/XMLSchema#integer"), objects)
        self.assertTrue(all(row["subject"].kind == "uri" for row in result.rows))

    def test_negative_ask_stays_boolean_and_prints_as_before(self):
        result = execute_query("ASK { ?s ?p ?o }", make_sparql_client({"boolean": False}))
        self.assertIs(result.rows[0]["boolean"], False)
        self.assertTrue(validate_results(result))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            display_results(result)
        self.assertEqual(output.getvalue(), "boolean: False\n")
        self.assertEqual(execute_sparql("ASK { ?s ?p ?o }", make_sparql_client({"boolean": False})), [{"boolean": "False"}])

    def test_pipeline_retains_metadata_until_display(self):
        result = QueryResult("SELECT", [{"label": Term("bonjour", "literal", language="fr")}])
        with mock.patch("nl2sparql.pipeline.execute_query", return_value=result):
            _, actual, valid = run_query_pipeline("Who?", lambda question: SIMPLE_QUERY)
            legacy = run_pipeline("Who?", lambda question: SIMPLE_QUERY)
        self.assertEqual(legacy, (SIMPLE_QUERY, [{"label": "bonjour"}], True))
        self.assertIs(actual, result)
        self.assertTrue(valid)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            display_results(actual)
        self.assertEqual(output.getvalue(), "label: bonjour\n")
        self.assertEqual(actual.rows[0]["label"].language, "fr")
        blank = QueryResult("SELECT", [{"label": Term(" ", "literal")}])
        with self.assertLogs("nl2sparql.validator", level="WARNING"):
            self.assertFalse(validate_results(blank))


class StartupTests(unittest.TestCase):
    def test_invalid_run_settings_prevent_generation_and_execution(self):
        cases = (
            (None, {"DBPEDIA_ENDPOINT": "file:///tmp/data"}),
            (None, {"DBPEDIA_ENDPOINT": "http://"}),
            (None, {"REQUEST_TIMEOUT_SECONDS": "0"}),
            (None, {"LOG_LEVEL": "invalid"}),
            ("openai", {"OPENAI_API_KEY": ""}),
            ("ollama", {"OLLAMA_HOST": "http://"}),
        )
        for backend, environment in cases:
            with self.subTest(backend=backend, environment=environment):
                generator = mock.Mock()
                with mock.patch.dict(os.environ, environment), mock.patch("nl2sparql.pipeline.execute_query") as execute:
                    with self.assertRaises(ConfigurationError):
                        run_pipeline("Who?", generator, backend=backend)
                    with self.assertLogs("nl2sparql.pipeline", level="ERROR"):
                        self.assertEqual(run_pipeline_cli("Who?", generator, backend=backend), 1)
                generator.assert_not_called()
                execute.assert_not_called()

    def test_one_settings_snapshot_reaches_both_clients(self):
        environment = {
            "OPENAI_API_KEY": "dummy-test-key", "OPENAI_MODEL": "test-model",
            "DBPEDIA_ENDPOINT": "https://example.test/sparql", "REQUEST_TIMEOUT_SECONDS": "7",
        }
        with mock.patch.dict(os.environ, environment):
            settings = load_settings("openai")
        self.assertNotIn("dummy-test-key", repr(settings))
        model_client = make_openai_client(SIMPLE_QUERY)
        transport = make_sparql_client({"results": {"bindings": []}})
        with mock.patch.dict(os.environ, {"DBPEDIA_ENDPOINT": "file:///bad", "REQUEST_TIMEOUT_SECONDS": "0", "OPENAI_MODEL": "changed"}):
            with mock.patch("nl2sparql.openai_backend.openai.OpenAI", return_value=model_client) as model_constructor:
                with mock.patch("nl2sparql.sparql_executor.SPARQLWrapper", return_value=mock.Mock(query=transport.query)) as endpoint_constructor:
                    with self.assertLogs("nl2sparql.validator", level="WARNING"):
                        run_pipeline("Who?", generate_sparql, backend="openai", settings=settings)
        model_constructor.assert_called_once_with(api_key="dummy-test-key", timeout=7)
        self.assertEqual(model_client.chat.completions.create.call_args.kwargs["model"], "test-model")
        self.assertEqual(endpoint_constructor.call_args.args[0], "https://example.test/sparql")
        endpoint_constructor.return_value.setTimeout.assert_called_once_with(7)

    def test_existing_launchers_work_outside_repository(self):
        root = Path(__file__).resolve().parents[1]
        environment = dict(os.environ, DBPEDIA_ENDPOINT="file:///invalid", OPENAI_API_KEY="", PYTHONDONTWRITEBYTECODE="1")
        for name in ("automate_queries", "automate_with_ollama", "pathology", "run_pathology_queries", "query_generator", "executor"):
            with self.subTest(name=name):
                completed = subprocess.run(
                    [sys.executable, str(root / f"{name}.py")], cwd="/tmp",
                    env=environment, capture_output=True, text=True, timeout=20,
                )
                self.assertEqual(completed.returncode, 1)
                self.assertIn("DBPEDIA_ENDPOINT", completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
