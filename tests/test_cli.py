"""Tests for the command line outcomes: exit codes, printed output, and failure handling."""

import contextlib
import io
import unittest
from unittest import mock

from nl2sparql import cli_openai as automate_queries
from nl2sparql import cli_ollama as automate_with_ollama
from nl2sparql import cli_pathology as pathology
from nl2sparql import cli_pathology_batch as run_pathology_queries
from nl2sparql.errors import (
    ConfigurationError,
    InvalidInputError,
    QueryExecutionError,
    QueryGenerationError,
)
from tests.fakes import SIMPLE_QUERY
from nl2sparql.pathology_queries import PATHOLOGY_QUERIES
from nl2sparql.pipeline import run_pipeline, run_pipeline_cli

EXIT_SUCCESS = 0
EXIT_PIPELINE_ERROR = 1
EXIT_RESULTS_NOT_MEANINGFUL = 2

QUESTION = "Who are some famous pathologists?"
MEANINGFUL_ROWS = [{"name": "Rudolf Virchow"}, {"name": "Karl Rokitansky"}]


def generate_simple_query(question):
    return SIMPLE_QUERY


def run_and_capture(function, *arguments):
    """Call the function. Return (its result, everything written to stdout)."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = function(*arguments)
    return result, output.getvalue()


class RunPipelineCliTests(unittest.TestCase):
    def setUp(self):
        # The real configure_logging would add a handler to the root logger of the test run.
        patcher = mock.patch("nl2sparql.pipeline.configure_logging")
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_cli(self, rows=None, execution_error=None, generate_sparql=generate_simple_query):
        """Run the CLI with a fake executor. Return (exit code, stdout, executor mock)."""
        with mock.patch(
            "nl2sparql.pipeline.execute_query", return_value=rows, side_effect=execution_error
        ) as execute:
            exit_code, output = run_and_capture(run_pipeline_cli, QUESTION, generate_sparql)
        return exit_code, output, execute

    def test_meaningful_results_exit_zero_and_are_printed(self):
        exit_code, output, execute = self.run_cli(rows=MEANINGFUL_ROWS)
        self.assertEqual(exit_code, EXIT_SUCCESS)
        execute.assert_called_once_with(SIMPLE_QUERY, settings=mock.ANY)
        self.assertIn(f"Generated SPARQL query:\n{SIMPLE_QUERY}\n", output)
        self.assertIn("name: Rudolf Virchow\n", output)
        self.assertIn("name: Karl Rokitansky\n", output)

    def test_question_reaches_the_generator(self):
        generate_sparql = mock.Mock(return_value=SIMPLE_QUERY)
        self.run_cli(rows=MEANINGFUL_ROWS, generate_sparql=generate_sparql)
        generate_sparql.assert_called_once_with(QUESTION)

    def test_empty_results_exit_two_and_say_so(self):
        with self.assertLogs("nl2sparql.pipeline", level="WARNING"):
            exit_code, output, _ = self.run_cli(rows=[])
        self.assertEqual(exit_code, EXIT_RESULTS_NOT_MEANINGFUL)
        self.assertIn("No results found.", output)
        self.assertIn(SIMPLE_QUERY, output)

    def test_blank_results_exit_two(self):
        for blank_rows in ([{"name": ""}], [{"name": "   "}], [{"name": "A"}, {"name": ""}], [{}]):
            with self.subTest(blank_rows=blank_rows):
                with self.assertLogs("nl2sparql.pipeline", level="WARNING"):
                    exit_code, _, _ = self.run_cli(rows=blank_rows)
                self.assertEqual(exit_code, EXIT_RESULTS_NOT_MEANINGFUL)

    def test_negative_ask_answer_is_success(self):
        exit_code, output, _ = self.run_cli(rows=[{"boolean": "False"}])
        self.assertEqual(exit_code, EXIT_SUCCESS)
        self.assertIn("boolean: False", output)

    def test_generation_failure_exits_one_and_prevents_execution(self):
        generation_errors = (
            QueryGenerationError("model returned prose"),
            InvalidInputError("question is empty"),
            ConfigurationError("OPENAI_API_KEY environment variable is not set"),
        )
        for error in generation_errors:
            with self.subTest(error=error):
                with self.assertLogs("nl2sparql.pipeline", level="ERROR") as logs:
                    exit_code, output, execute = self.run_cli(
                        rows=MEANINGFUL_ROWS, generate_sparql=mock.Mock(side_effect=error)
                    )
                self.assertEqual(exit_code, EXIT_PIPELINE_ERROR)
                execute.assert_not_called()
                self.assertEqual(output, "")
                self.assertIn(str(error), logs.output[0])

    def test_execution_failure_exits_one_and_prints_no_results(self):
        with self.assertLogs("nl2sparql.pipeline", level="ERROR"):
            exit_code, output, execute = self.run_cli(
                execution_error=QueryExecutionError("endpoint is down")
            )
        self.assertEqual(exit_code, EXIT_PIPELINE_ERROR)
        execute.assert_called_once_with(SIMPLE_QUERY, settings=mock.ANY)
        self.assertNotIn("name:", output)
        self.assertNotIn("No results found.", output)

    def test_hostile_generated_query_is_refused_before_the_endpoint(self):
        hostile_queries = ("DROP ALL", "SELECT ?s WHERE { SERVICE <http://127.0.0.1/> { ?s ?p ?o } }")
        for hostile_query in hostile_queries:
            with self.subTest(hostile_query=hostile_query):
                with mock.patch("nl2sparql.sparql_executor.fetch_response") as fetch:
                    with self.assertLogs("nl2sparql.pipeline", level="ERROR"):
                        exit_code, _ = run_and_capture(
                            run_pipeline_cli, QUESTION, lambda question: hostile_query
                        )
                self.assertEqual(exit_code, EXIT_PIPELINE_ERROR)
                fetch.assert_not_called()

    def test_run_pipeline_reports_empty_results_as_not_valid(self):
        with mock.patch("nl2sparql.pipeline.execute_query", return_value=[]):
            with self.assertLogs("nl2sparql.validator", level="WARNING"):
                outcome = run_pipeline(QUESTION, generate_simple_query)
        self.assertEqual(outcome, (SIMPLE_QUERY, [], False))

    def test_run_pipeline_lets_domain_errors_reach_the_caller(self):
        with mock.patch("nl2sparql.pipeline.execute_query", side_effect=QueryExecutionError("down")):
            with self.assertRaises(QueryExecutionError):
                run_pipeline(QUESTION, generate_simple_query)


class ScriptEntryPointTests(unittest.TestCase):
    def test_each_script_runs_the_pipeline_with_its_own_backend(self):
        scripts = (
            (automate_queries, automate_queries.generate_sparql),
            (automate_with_ollama, automate_with_ollama.generate_sparql_with_ollama),
        )
        for script, expected_backend in scripts:
            for exit_code in (EXIT_SUCCESS, EXIT_PIPELINE_ERROR, EXIT_RESULTS_NOT_MEANINGFUL):
                with self.subTest(script=script.__name__, exit_code=exit_code):
                    with mock.patch.object(
                        script, "run_pipeline_cli", return_value=exit_code
                    ) as run_cli:
                        self.assertEqual(script.main(), exit_code)
                    run_cli.assert_called_once_with(
                        script.natural_query, expected_backend,
                        backend="openai" if script is automate_queries else "ollama",
                    )


class PathologyBatchTests(unittest.TestCase):
    def setUp(self):
        for module_name in ("nl2sparql.cli_pathology_batch", "nl2sparql.cli_pathology"):
            patcher = mock.patch(f"{module_name}.configure_logging")
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_batch(self, outcomes):
        """Run the batch with one executor outcome per query. Return (code, stdout, mock)."""
        with mock.patch("nl2sparql.cli_pathology_batch.execute_query", side_effect=outcomes) as execute:
            exit_code, output = run_and_capture(run_pathology_queries.main)
        return exit_code, output, execute

    def test_all_queries_succeed(self):
        outcomes = [[{"name": f"result {index}"}] for index in range(len(PATHOLOGY_QUERIES))]
        exit_code, output, execute = self.run_batch(outcomes)
        self.assertEqual(exit_code, EXIT_SUCCESS)
        sent_queries = [call.args[0] for call in execute.call_args_list]
        self.assertEqual(sent_queries, list(PATHOLOGY_QUERIES.values()))
        for index, title in enumerate(PATHOLOGY_QUERIES):
            self.assertIn(f"=== {title} ===\nname: result {index}\n", output)

    def test_one_failure_still_runs_the_rest_and_exits_one(self):
        for failing_index in range(len(PATHOLOGY_QUERIES)):
            with self.subTest(failing_index=failing_index):
                outcomes = [[{"name": "ok"}] for _ in PATHOLOGY_QUERIES]
                outcomes[failing_index] = QueryExecutionError("endpoint is down")
                with self.assertLogs("nl2sparql.cli_pathology_batch", level="ERROR") as logs:
                    exit_code, output, execute = self.run_batch(outcomes)
                self.assertEqual(exit_code, EXIT_PIPELINE_ERROR)
                self.assertEqual(execute.call_count, len(PATHOLOGY_QUERIES))
                self.assertEqual(output.count("name: ok"), len(PATHOLOGY_QUERIES) - 1)
                self.assertEqual(len(logs.output), 1)
                self.assertIn(list(PATHOLOGY_QUERIES)[failing_index], logs.output[0])

    def test_every_query_failing_exits_one(self):
        outcomes = [QueryExecutionError("down") for _ in PATHOLOGY_QUERIES]
        with self.assertLogs("nl2sparql.cli_pathology_batch", level="ERROR"):
            exit_code, output, execute = self.run_batch(outcomes)
        self.assertEqual(exit_code, EXIT_PIPELINE_ERROR)
        self.assertEqual(execute.call_count, len(PATHOLOGY_QUERIES))
        self.assertNotIn("name:", output)

    def test_empty_results_are_shown_and_do_not_fail_the_batch(self):
        exit_code, output, _ = self.run_batch([[] for _ in PATHOLOGY_QUERIES])
        self.assertEqual(exit_code, EXIT_SUCCESS)
        self.assertEqual(output.count("No results found."), len(PATHOLOGY_QUERIES))

    def test_predefined_queries_pass_validation(self):
        with mock.patch("nl2sparql.sparql_executor.fetch_response") as fetch:
            fetch.return_value = ("application/sparql-results+json", b'{"results": {"bindings": []}}')
            with mock.patch("nl2sparql.sparql_executor.create_sparql_client"):
                exit_code, _ = run_and_capture(run_pathology_queries.main)
        self.assertEqual(exit_code, EXIT_SUCCESS)
        self.assertEqual(fetch.call_count, len(PATHOLOGY_QUERIES))

    def test_single_query_script_exit_codes(self):
        with mock.patch("nl2sparql.cli_pathology_batch.execute_query", return_value=MEANINGFUL_ROWS):
            exit_code, output = run_and_capture(pathology.main)
        self.assertEqual(exit_code, EXIT_SUCCESS)
        self.assertIn("name: Rudolf Virchow", output)
        failure = QueryExecutionError("down")
        with mock.patch("nl2sparql.cli_pathology_batch.execute_query", side_effect=failure):
            with self.assertLogs("nl2sparql.cli_pathology_batch", level="ERROR"):
                exit_code, _ = run_and_capture(pathology.main)
        self.assertEqual(exit_code, EXIT_PIPELINE_ERROR)


if __name__ == "__main__":
    unittest.main()
