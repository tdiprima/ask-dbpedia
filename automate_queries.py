"""Fully automated run: natural language -> GPT-5.2 -> DBPedia -> printed results."""

import sys

from pipeline import run_pipeline_cli
from query_generator import generate_sparql

natural_query = "Who are some famous pathologists?"


def main():
    return run_pipeline_cli(natural_query, generate_sparql)


if __name__ == "__main__":
    sys.exit(main())
