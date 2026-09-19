"""Compatibility launcher; implementation lives in cli_ollama."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cli_ollama import main as run

from ollama_backend import generate_sparql_with_ollama

natural_query = "Who are some famous pathologists?"


def main():
    return run(natural_query)


if __name__ == "__main__":
    raise SystemExit(main())
