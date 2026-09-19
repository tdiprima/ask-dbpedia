"""Compatibility launcher and public API imports."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cli_execute import main
from sparql_executor import execute_sparql, execute_query

if __name__ == "__main__":
    raise SystemExit(main())
