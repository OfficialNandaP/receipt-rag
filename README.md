# Receipt RAG and Customer CSV Analysis

This repository contains two related examples:

- A local receipt question-answering workflow using retrieval-augmented generation (RAG).
- A pandas notebook for profiling customer CSV data and processing a 2-million-row CSV with bounded memory.

## Repository Contents

- `rag/`: receipt ingestion, normalization, retrieval, reranking, and LLM integration.
- `examples/simple_rag_bm25_ollama.py`: command-line RAG example.
- `examples/simple_rag_bm25_ollama_ui.py`: Streamlit RAG example.
- `examples/customer_csv_analysis.ipynb`: customer CSV profiling and chunked large-file analysis.
- `dataset/customers-100000.csv`: dataset used for the detailed in-memory profile.
- `dataset/customers-2000000/customers-2000000.csv`: large dataset used for chunked processing.

## Receipt MVP

Install the receipt dependencies:

```bash
python -m pip install -r requirements-receipt.txt
```

### Streamlit Web App

Start the Streamlit receipt application from the repository root:

```bash
streamlit run examples/simple_rag_bm25_ollama_ui.py
```

The web app lets you upload or enter receipt content, normalize it, store it in SQLite, and ask questions using the local RAG pipeline. Keep the terminal running while using the app; Streamlit prints the local browser URL when it starts.

The app stores normalized receipts in SQLite. Paste normalized JSON into the OCR text box while the Azure OCR adapter is being configured:

`AZURE_OPENAI_DEPLOYMENT` must be the exact deployment name shown in your Azure AI Foundry project, not necessarily the base model name. For example, if the deployment is named `receipt-gpt`, set `AZURE_OPENAI_DEPLOYMENT=receipt-gpt`.

For the OpenAI-compatible endpoint format, use an endpoint ending in `/openai/v1` and the matching model or deployment identifier. Do not append `/openai/v1` to a classic Azure OpenAI endpoint unless your resource explicitly provides that route.

```json
{"merchant_name":"Shop","receipt_date":"2026-06-20","currency":"USD","subtotal":"10.00","tax":"2.50","total":"12.50","items":[{"name":"Burger","quantity":1,"unit_price":"12.50","line_total":"12.50","category":"food"}]}
```
This is a simple RAG (Retrieval-Augmented Generation) implementation. Its main modules are:
- **Retrieval**: Retrieves relevant documents from a corpus.
- **Rerank**: Reranks retrieved documents.
- **LLM**: Generates an answer from the retrieved context.
- **Data Helper**: Loads source PDF data.


## Installation

**Prerequisites**:
- Python 3.10 or later recommended
- Ollama (for LLM self-hosted)
- Poppler (for PDF processing)

To install poppler, select one of the following commands that is appropriate for your OS:
```bash
# Debian/Ubuntu
sudo apt install build-essential libpoppler-cpp-dev pkg-config python3-dev

# Fedora/RHEL
sudo yum install gcc-c++ pkgconfig poppler-cpp-devel python3-devel

# macOS
brew install pkg-config poppler python

# Windows (using conda)
conda install -c conda-forge poppler
```

Then, install the package using the following commands:
```bash
git clone https://github.com/behitek/simple-rag/
cd simple-rag
pip install -e .
```

## RAG CLI Example

Run the command-line example:

```bash
python examples/simple_rag_bm25_ollama.py
```

It ingests a PDF, answers an initial query, and then prompts for additional questions.

For programmatic use, the core pipeline looks like this:

```python
import os

from rag.data_helper import PDFReader
from rag.llm import OllamaLLM
from rag.pipeline import Answer, SimpleRAGPipeline
from rag.rerank import CrossEncoderRerank
from rag.retrieval import BM25Retrieval
from rag.text_utils import text2chunk

# Set your PDF path here
sample_pdf = os.path.join(os.path.dirname(__file__), "sample.pdf")
contents = PDFReader(pdf_paths=[sample_pdf]).read()
text = " ".join(contents)
chunks = text2chunk(text, chunk_size=200, overlap=50)
print(f"Number of chunks: {len(chunks)}")

retrieval = BM25Retrieval(documents=chunks)
llm = OllamaLLM(model_name="llama3:instruct")
rerank = CrossEncoderRerank(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
pipeline = SimpleRAGPipeline(retrieval=retrieval, llm=llm, rerank=rerank)


def run(query: str) -> Answer:
    return pipeline.run(query)


if __name__ == "__main__":
    query = "What can Ollama do?"
    print("Sample query:", query)
    response: Answer = pipeline.run(query)
    print(response.answer)
    print("Now, please ask your own questions!")
    while True:
        query = input("Your question: ")
        response: Answer = run(query)
        print(response.answer)
        print()
```

Example result:
```bash
$ python examples/simple_rag_bm25_ollama.py

Number of chunks: 10
Sample query: What can Ollama do?
Based on the provided context, what can Ollama do?

According to the text, Ollama can:

1. Self-host a lot of "top" open-source LLMs, including LLAMA2 (by Facebook), Mistral, Phi (from Microsoft), Gemma (by Google), and more.
2. Deploy a model with custom parameters.
3. Deploy a custom model from .GGUF format.
4. Support 4-bit quantization to save memory.
5. Handle several GPU types: NVIDIA, AMD, and Apple GPU.
6. Provide an OpenAI-compatible API.

Additionally, Ollama can also:

1. Run on multiple platforms: Windows (preview), MacOS, and Linux.
2. Deploy LLM without a GPU, although this is not explicitly tested in the context.
```

## Customer CSV Analysis

The notebook [examples/customer_csv_analysis.ipynb](examples/customer_csv_analysis.ipynb) answers two data-analysis questions:

1. Parse `customers-100000.csv` and report dataset shape, dtypes, memory usage, missing values, duplicates, cardinality, countries, subscription years, and email domains.
2. Parse `customers-2000000.csv` without loading the entire file into memory.

The large-file workflow uses `pandas.read_csv(..., chunksize=50_000)`, explicit dtypes, and aggregate counters. It retains only summary statistics and a five-row sample while processing all 2,000,000 rows.

Install the notebook dependency if needed:

```bash
python -m pip install pandas jupyter
```

Start Jupyter from the repository root:

```bash
jupyter notebook examples/customer_csv_analysis.ipynb
```

The notebook expects the datasets at the paths shown in the repository tree. It can also be run from VS Code with the Python and Jupyter extensions installed.

## Example Files

- `examples/simple_rag_bm25_ollama.py`: command-line RAG example.
- `examples/simple_rag_bm25_ollama_ui.py`: Streamlit RAG web app.
- `examples/customer_csv_analysis.ipynb`: customer CSV profiling and low-memory large-file analysis.