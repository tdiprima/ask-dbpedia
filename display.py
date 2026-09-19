"""Render query results as readable text on standard output."""

import sys


def write_line(text):
    """Write one line of program output (not a log message)."""
    sys.stdout.write(f"{text}\n")


def format_row(row):
    """Return one result row as 'name: value' pairs."""
    return " | ".join(f"{name}: {value}" for name, value in row.items())


def display_results(results):
    """Write every result row, or a notice when there are none."""
    if not results:
        write_line("No results found.")
        return
    for row in results:
        write_line(format_row(row))
