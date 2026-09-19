"""Same as automate_queries.py, but uses a local Ollama model instead of OpenAI.

Note: OpenAI's GPT-5.2 performs better than Ollama's Mistral at writing SPARQL.
"""

import logging

import httpx
import ollama

from config import load_settings, get_ollama_model
from errors import QueryGenerationError
from sparql_text import build_chat_messages, extract_sparql

logger = logging.getLogger(__name__)


def generate_sparql_with_ollama(question, client=None, *, settings=None):
    """Return a read-only SPARQL query written by the local Ollama model."""
    messages = build_chat_messages(question)
    if client is None:
        settings = settings or load_settings("ollama")
        client = ollama.Client(host=settings.ollama_host, timeout=settings.timeout)
    model = settings.model if settings else get_ollama_model()
    try:
        response = client.chat(model=model, messages=messages)
    except (
        ollama.ResponseError,
        ollama.RequestError,
        httpx.HTTPError,
        ConnectionError,
    ) as error:
        logger.error("ollama_request_failed model=%s error=%s", model, error)
        raise QueryGenerationError(f"Ollama request failed: {error}") from error
    return extract_sparql(read_reply_text(response))


def read_reply_text(response):
    """Return the reply text from an Ollama chat response."""
    try:
        return response["message"]["content"]
    except (KeyError, TypeError) as error:
        logger.error("ollama_reply_malformed error=%r", error)
        raise QueryGenerationError("Ollama reply has no message content") from error
