"""Compatibility launcher; implementation lives in cli_openai."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cli_openai import main as run

from openai_backend import generate_sparql

natural_query = "Who are some famous pathologists?"


def main():
    return run(natural_query)


if __name__ == "__main__":
    raise SystemExit(main())
