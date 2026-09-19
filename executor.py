"""Compatibility launcher and public API imports."""
from nl2sparql.cli_execute import main
from nl2sparql.sparql_executor import execute_sparql, execute_query

if __name__ == "__main__":
    raise SystemExit(main())
