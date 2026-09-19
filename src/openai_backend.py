"""Convert natural language into a SPARQL query with OpenAI GPT-5.2."""

import logging

import openai

from config import load_settings, get_openai_model
from errors import QueryGenerationError
from sparql_text import build_chat_messages, extract_sparql

logger = logging.getLogger(__name__)

EXAMPLE_NATURAL_QUERY = "List all Nobel Prize winners in Physics after 2000"


def create_openai_client(*, settings=None):
    """Build an OpenAI client from environment configuration."""
    settings = settings or load_settings("openai")
    return openai.OpenAI(api_key=settings.api_key, timeout=settings.timeout)


def generate_sparql(natural_query, client=None, *, settings=None):
    """Return a read-only SPARQL query for the natural language question."""
    messages = build_chat_messages(natural_query)
    if client is None:
        settings = settings or load_settings("openai")
        client = create_openai_client(settings=settings)
    model = settings.model if settings else get_openai_model()
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
