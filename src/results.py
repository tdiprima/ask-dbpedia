"""Result values retained independently of transport and terminal formatting."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Term:
    value: str
    kind: str
    datatype: str | None = None
    language: str | None = None


@dataclass
class QueryResult:
    form: str
    rows: list[dict[str, Term | bool]]

    def text_rows(self):
        """Legacy string-row view; prefer rows when RDF identity matters."""
        return [
            {name: value.value if isinstance(value, Term) else str(value)
             for name, value in row.items()}
            for row in self.rows
        ]
