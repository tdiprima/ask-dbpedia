"""Configuration loaded from environment variables, with sane defaults."""

import os
import logging
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from nl2sparql.errors import ConfigurationError

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
    validate_url("DBPEDIA_ENDPOINT", endpoint)
    return endpoint


def get_openai_model():
    return get_setting("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def get_ollama_model():
    return get_setting("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def get_ollama_host():
    return get_setting("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)


def get_log_level():
    return get_setting("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()


def validate_url(name, value):
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("missing HTTP(S) host")
        parsed.port
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an http(s) URL with a valid host and port") from error
    return value


@dataclass(frozen=True)
class Settings:
    endpoint: str
    timeout: int
    log_level: str
    backend: str | None = None
    model: str | None = None
    ollama_host: str | None = None
    api_key: str | None = field(default=None, repr=False)


def load_settings(backend=None):
    """Validate a complete run before creating clients or making requests."""
    if backend not in (None, "openai", "ollama"):
        raise ConfigurationError(f"Unknown backend: {backend!r}")
    endpoint = get_dbpedia_endpoint()
    timeout = get_request_timeout_seconds()
    level = get_log_level()
    if not isinstance(logging.getLevelName(level), int):
        raise ConfigurationError(f"LOG_LEVEL is not a valid level: {level!r}")
    model = host = api_key = None
    if backend == "openai":
        model, api_key = get_openai_model(), get_openai_api_key()
    elif backend == "ollama":
        model = get_ollama_model()
        host = validate_url("OLLAMA_HOST", get_ollama_host())
    return Settings(
        endpoint=endpoint, timeout=timeout, log_level=level, backend=backend,
        model=model, ollama_host=host, api_key=api_key,
    )
