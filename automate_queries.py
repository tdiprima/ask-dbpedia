"""Compatibility launcher; implementation lives in cli_openai."""
from nl2sparql.cli_openai import main as run


natural_query = "Who are some famous pathologists?"


def main():
    return run(natural_query)


if __name__ == "__main__":
    raise SystemExit(main())
