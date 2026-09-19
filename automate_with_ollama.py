"""Same as automate_queries.py, but uses a local Ollama model instead of OpenAI.

Note: OpenAI's GPT-5.2 performs better than Ollama's Mistral at writing SPARQL.
"""

import logging
import sys

import httpx
import ollama

from config import get_ollama_host, get_ollama_model, get_request_timeout_seconds
from errors import QueryGenerationError
from pipeline import run_pipeline_cli
from sparql_text import build_chat_messages, extract_sparql

logger = logging.getLogger(__name__)

natural_query = "Who are some famous pathologists?"


def generate_sparql_with_ollama(question, client=None):
    """Return a read-only SPARQL query written by the local Ollama model."""
    messages = build_chat_messages(question)
    if client is None:
        client = ollama.Client(
            host=get_ollama_host(), timeout=get_request_timeout_seconds()
        )
    model = get_ollama_model()
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


def main():
    return run_pipeline_cli(natural_query, generate_sparql_with_ollama)


if __name__ == "__main__":
    sys.exit(main())
