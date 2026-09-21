"""Fully automated run: natural language -> GPT-5.2 -> DBPedia -> printed results."""

import sys

from nl2sparql.pipeline import run_pipeline_cli
from nl2sparql.openai_backend import generate_sparql

natural_query = "Who are some famous pathologists?"


def main(question=None):
    return run_pipeline_cli(natural_query if question is None else question, generate_sparql, backend="openai")


if __name__ == "__main__":
    sys.exit(main())
