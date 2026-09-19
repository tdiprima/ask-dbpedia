"""Domain errors for the natural language to SPARQL pipeline."""


class Nl2SparqlError(Exception):
    """Base class for all errors raised by this project."""


class ConfigurationError(Nl2SparqlError):
    """Configuration is missing or invalid."""


class InvalidInputError(Nl2SparqlError):
    """Caller supplied input that failed validation."""


class QueryGenerationError(Nl2SparqlError):
    """The language model did not produce a usable SPARQL query."""


class QueryExecutionError(Nl2SparqlError):
    """The SPARQL endpoint rejected the query or did not respond."""
