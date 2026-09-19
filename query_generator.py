"""Convert natural language into a SPARQL query with OpenAI GPT-5.2."""

import logging
import sys

import openai

from config import get_openai_api_key, get_openai_model, get_request_timeout_seconds
from display import write_line
from errors import Nl2SparqlError, QueryGenerationError
from logging_setup import configure_logging
from sparql_text import build_chat_messages, extract_sparql

logger = logging.getLogger(__name__)

EXAMPLE_NATURAL_QUERY = "List all Nobel Prize winners in Physics after 2000"


def create_openai_client():
    """Build an OpenAI client from environment configuration."""
    return openai.OpenAI(
        api_key=get_openai_api_key(), timeout=get_request_timeout_seconds()
    )


def generate_sparql(natural_query, client=None):
    """Return a read-only SPARQL query for the natural language question."""
    messages = build_chat_messages(natural_query)
    if client is None:
        client = create_openai_client()
    model = get_openai_model()
    try:
        completion = client.chat.completions.create(
            model=model, messages=messages
        )
    except openai.OpenAIError as error:
        logger.error("openai_request_failed model=%s error=%s", model, error)
        raise QueryGenerationError(f"OpenAI request failed: {error}") from error
    if not completion.choices:
        raise QueryGenerationError("OpenAI returned no choices")
    sparql_query = extract_sparql(completion.choices[0].message.content)
    logger.info("sparql_generated model=%s length=%d", model, len(sparql_query))
    return sparql_query


def main():
    configure_logging()
    try:
        write_line(generate_sparql(EXAMPLE_NATURAL_QUERY))
    except Nl2SparqlError as error:
        logger.error("query_generation_failed error=%s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
