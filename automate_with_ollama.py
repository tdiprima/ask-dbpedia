"""Compatibility launcher; implementation lives in cli_ollama."""
from nl2sparql.cli_ollama import main as run


natural_query = "Who are some famous pathologists?"


def main():
    try:
        return run(natural_query)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
