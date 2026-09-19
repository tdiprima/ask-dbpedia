# nl2sparql

[![CI](https://github.com/tdiprima/nl2sparql/actions/workflows/ci.yml/badge.svg)](https://github.com/tdiprima/nl2sparql/actions/workflows/ci.yml)

Ask DBpedia questions in plain English: an LLM writes the SPARQL, the pipeline runs it and validates the answer.

## Knowledge Graphs Speak SPARQL, Not English

DBpedia holds structured facts from Wikipedia, but you can only reach them through SPARQL. Writing SPARQL means knowing the ontology (`dbo:`, `dbr:`, `dbp:`), the right predicates, and query syntax. That blocks analysts, researchers, and clinicians who know the question but not the query language. LLMs can bridge the gap, but their output is untrusted. It may arrive wrapped in markdown, contain write operations, or return nothing useful.

## From Question to Verified Answer

nl2sparql chains four guarded stages:

1. **Generate**: OpenAI (default `gpt-5.2`) or a local Ollama model (default `mistral`) turns the question into SPARQL using a DBpedia-aware system prompt.
2. **Sanitize**: Code fences and stray prose are stripped. Only read-only forms (`SELECT`, `ASK`, `DESCRIBE`, `CONSTRUCT`) pass. Input and query length are capped.
3. **Execute**: The query runs against the DBpedia endpoint via SPARQLWrapper with a timeout and a descriptive user agent.
4. **Validate**: Empty or blank results are flagged, and the CLI exits with a distinct code (`2`).

Design highlights:
- Swappable LLM backends behind one shared pipeline
- Domain-specific exceptions and structured logging
- Env-var configuration, with the API key never hardcoded
- Offline unit tests with fakes, plus live tests in CI

## See It Work

Question: `Who are some famous pathologists?`

The pipeline prints the generated SPARQL, then result rows as `name: value` pairs. Exit codes: `0` success, `1` pipeline error, `2` results not meaningful.

A curated set of five pathology queries also ships ready to run: common diseases, cancers with ICD-10 codes, liver diseases, pathology scientists, and diseases by medical specialty.

## Get Started

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Run with OpenAI:

```bash
export OPENAI_API_KEY="your-key"
uv run python automate_queries.py
```

Run with a local Ollama model, no API key needed:

```bash
ollama pull mistral
uv run python automate_with_ollama.py
```

Edit `natural_query` in either script to ask your own question.

Run the pre-defined pathology queries with no LLM:

```bash
uv run python run_pathology_queries.py
uv run python pathology.py
```

Run the tests:

```bash
uv run python -m unittest test_queries
```

Optional environment variables:

| Variable | Default |
|---|---|
| `OPENAI_MODEL` | `gpt-5.2` |
| `OLLAMA_MODEL` | `mistral` |
| `OLLAMA_HOST` | `http://localhost:11434` |
| `DBPEDIA_ENDPOINT` | `https://dbpedia.org/sparql` |
| `REQUEST_TIMEOUT_SECONDS` | `30` (max `300`) |
| `LOG_LEVEL` | `INFO` |

GPT-5.2 writes better SPARQL than Mistral, so use OpenAI when accuracy matters.

## License

See [LICENSE](LICENSE).
