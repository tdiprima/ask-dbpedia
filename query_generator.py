"""Compatibility launcher and public API imports."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cli_generate import main
from openai_backend import generate_sparql, create_openai_client

if __name__ == "__main__":
    raise SystemExit(main())
