## Running the Scripts

Run each script from the **repo root** with:

```bash
uv run python <script>
```

<br>

| Script                     | What it does                                                                                        | Needs            |
| -------------------------- | --------------------------------------------------------------------------------------------------- | ---------------- |
| `automate_queries.py`      | Turns the question into SPARQL with OpenAI, runs it on DBpedia, and prints the results.             | `OPENAI_API_KEY` |
| `automate_with_ollama.py`  | Same as above, but uses a local Ollama model.                                                       | Ollama running   |
| `query_generator.py`       | Only generates SPARQL for a built-in example question and prints it. **It does not run the query.** | `OPENAI_API_KEY` |
| `executor.py`              | Only runs a built-in example SPARQL query on DBpedia and prints the results. **No LLM.**            | Nothing          |
| `pathology.py`             | Runs the single **"Pathology scientists"** query. **No LLM.**                                       | Nothing          |
| `run_pathology_queries.py` | Runs all **5 pathology queries** in a batch. **No LLM.**                                            | Nothing          |

### Changing the Question

For the first two scripts:

* `automate_queries.py`
* `automate_with_ollama.py`

Edit the `natural_query` variable inside the file to change the question.

> **Note:** None of these scripts take command-line arguments. The questions and queries are currently **hardcoded**.

<br>
