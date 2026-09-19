"""Configuration loaded from environment variables, with sane defaults."""

import os

from errors import ConfigurationError

DEFAULT_DBPEDIA_ENDPOINT = "https://dbpedia.org/sparql"
DEFAULT_OPENAI_MODEL = "gpt-5.2"
DEFAULT_OLLAMA_MODEL = "mistral"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_LOG_LEVEL = "INFO"

MAX_REQUEST_TIMEOUT_SECONDS = 300


def get_setting(name, default):
    """Return a non-empty environment value, or the default."""
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    return value


def get_openai_api_key():
    """Return the OpenAI API key. Fail immediately when it is missing."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError("OPENAI_API_KEY environment variable is not set")
    return api_key


def get_request_timeout_seconds():
    """Return the validated network timeout in seconds."""
    raw_value = get_setting(
        "REQUEST_TIMEOUT_SECONDS", str(DEFAULT_REQUEST_TIMEOUT_SECONDS)
    )
    try:
        timeout_seconds = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(
            f"REQUEST_TIMEOUT_SECONDS must be an integer, got {raw_value!r}"
        ) from error
    if not 1 <= timeout_seconds <= MAX_REQUEST_TIMEOUT_SECONDS:
        raise ConfigurationError(
            f"REQUEST_TIMEOUT_SECONDS must be between 1 and {MAX_REQUEST_TIMEOUT_SECONDS}"
        )
    return timeout_seconds


def get_dbpedia_endpoint():
    """Return the validated SPARQL endpoint URL."""
    endpoint = get_setting("DBPEDIA_ENDPOINT", DEFAULT_DBPEDIA_ENDPOINT)
    if not endpoint.startswith(("https://", "http://")):
        raise ConfigurationError("DBPEDIA_ENDPOINT must be an http(s) URL")
    return endpoint


def get_openai_model():
    return get_setting("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def get_ollama_model():
    return get_setting("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def get_ollama_host():
    return get_setting("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)


def get_log_level():
    return get_setting("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
