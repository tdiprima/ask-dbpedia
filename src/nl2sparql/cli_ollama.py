"""Run the natural-language pipeline with Ollama."""
from ollama_backend import generate_sparql_with_ollama
from pipeline import run_pipeline_cli

natural_query = "Who are some famous pathologists?"


def main(question=None):
    return run_pipeline_cli(
        natural_query if question is None else question,
        generate_sparql_with_ollama, backend="ollama",
    )


if __name__ == "__main__":
    raise SystemExit(main())
