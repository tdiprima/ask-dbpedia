"""Compatibility launcher for the CLI in src/."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cli_pathology import main

if __name__ == "__main__":
    raise SystemExit(main())
