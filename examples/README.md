# Examples

Install the project dependencies by following the instructions in the [project README](../README.md).

## Customer CSV Analysis Notebook

Open [customer_csv_analysis.ipynb](customer_csv_analysis.ipynb) to:

- Profile `dataset/customers-100000.csv` in detail.
- Inspect row counts, columns, dtypes, memory usage, missing values, duplicates, unique values, countries, subscription years, and email domains.
- Process `dataset/customers-2000000/customers-2000000.csv` in 50,000-row chunks.
- Keep large-file memory bounded by retaining aggregate counters and a small sample rather than the full DataFrame.

Install the notebook dependencies and open it from the repository root:

```bash
python -m pip install pandas jupyter
jupyter notebook examples/customer_csv_analysis.ipynb
```

The notebook validates that the small file contains 100,000 rows and that the large file can be processed in chunks across all 2,000,000 rows.

## RAG CLI Example
The CLI example is currently ingesting a PDF file and answer the initial query. The user can then ask their own questions.

```bash
python examples/simple_rag_bm25_ollama.py
```

## RAG Streamlit Example (Web App)

The Streamlit example is a simple web app that allows the user to input PDF file to ingest and ask questions.

```bash
streamlit run examples/simple_rag_bm25_ollama_ui.py
```

![RAG Streamlit UI](../assets/ui.png)