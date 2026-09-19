"""Render query results as readable text on standard output.

Everything written here may come from the SPARQL endpoint or the language
model, so terminal control characters are shown as harmless text.
"""

import sys
import unicodedata

from results import QueryResult, Term

CONTROL_CATEGORIES = ("Cc", "Zl", "Zp")
# Bidirectional controls can reorder text on screen and spoof what a row says.
# Written as code points so this file holds no invisible characters itself.
BIDI_CONTROL_CODE_POINTS = (
    0x061C, 0x200E, 0x200F,
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
)
BIDI_CONTROL_CHARACTERS = frozenset(chr(code_point) for code_point in BIDI_CONTROL_CODE_POINTS)
LINE_LAYOUT_CHARACTERS = "\n\t"


def is_control_character(character):
    """True for characters that can move the cursor, clear the screen, or reorder text."""
    if character in BIDI_CONTROL_CHARACTERS:
        return True
    return unicodedata.category(character) in CONTROL_CATEGORIES


def escape_character(character):
    """Return a visible form such as \\x1b or \\u202e."""
    code_point = ord(character)
    if code_point <= 0xFF:
        return f"\\x{code_point:02x}"
    return f"\\u{code_point:04x}"


def escape_control_characters(text, keep=""):
    """Replace control characters with visible text, except the ones in keep."""
    return "".join(
        escape_character(character)
        if is_control_character(character) and character not in keep
        else character
        for character in str(text.value if isinstance(text, Term) else text)
    )


def write_line(text):
    """Write one line of program output (not a log message)."""
    # Generated queries span several lines, so newlines and tabs stay.
    readable_text = str(text).replace("\r\n", "\n")
    safe_text = escape_control_characters(readable_text, keep=LINE_LAYOUT_CHARACTERS)
    sys.stdout.write(f"{safe_text}\n")


def format_row(row):
    """Return one result row as 'name: value' pairs."""
    # A newline inside a value could fake an extra row, so nothing is kept here.
    return " | ".join(
        f"{escape_control_characters(name)}: {escape_control_characters(value)}"
        for name, value in row.items()
    )


def display_results(results):
    """Write every result row, or a notice when there are none."""
    if isinstance(results, QueryResult):
        results = results.rows
    if not results:
        write_line("No results found.")
        return
    for row in results:
        write_line(format_row(row))
