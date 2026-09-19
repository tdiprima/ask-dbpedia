"""Compatibility launcher; implementation lives in cli_ollama."""
from nl2sparql.cli_ollama import main as run

from nl2sparql.ollama_backend import generate_sparql_with_ollama

natural_query = "Who are some famous pathologists?"


def main():
    return run(natural_query)


if __name__ == "__main__":
    raise SystemExit(main())
