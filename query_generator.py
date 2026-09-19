"""Compatibility launcher and public API imports."""
from nl2sparql.cli_generate import main
from nl2sparql.openai_backend import generate_sparql, create_openai_client

if __name__ == "__main__":
    raise SystemExit(main())
