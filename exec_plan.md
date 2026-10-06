## Recommended Approach

Fork the repository and keep its existing `rag` package as the application core. Replace the PDF-only demo flow with a small Streamlit receipt app, using:

- Azure Document Intelligence for image OCR.
- Azure OpenAI for normalization into a strict receipt JSON structure.
- SQLite for structured receipt and line-item storage.
- A file-backed local vector index implemented with Python lists/JSON and manual cosine similarity.
- A thin query service that uses SQL for exact date/category/expense questions and vector retrieval plus Azure OpenAI for natural-language product/store questions.
- Docker Compose for local execution and GitHub Actions for tests and image/build validation.

Avoid microservices, a separate frontend framework, and a high-level vector database in the MVP.

## Phase 1: Establish the Application Shell

**Goal:** Convert the PDF demo into a receipt-focused application entry point.

**Files/modules likely to change:**

- `simple_rag_bm25_ollama_ui.py`
- `__init__.py`
- `requirements.txt`
- `setup.py`
- `.env.example`
- `README.md`

**What to implement:**

- Rename or replace the current Streamlit UI with a receipt upload interface.
- Accept common image formats such as PNG, JPEG, and WEBP.
- Add configuration loading for:
  - Azure Document Intelligence endpoint and key.
  - Azure OpenAI endpoint, API key, deployment name, and API version.
  - SQLite database path.
  - Local vector index path.
- Add Streamlit dependencies and Azure SDK dependencies.
- Keep the existing CLI/PDF examples temporarily if useful, but make the receipt app the documented primary entry point.

**Why it is needed:**

The current UI is tightly coupled to temporary PDFs and an in-memory RAG pipeline. The receipt app needs a persistent application flow and environment configuration before OCR and storage can be added.

## Phase 2: Add Receipt OCR

**Goal:** Extract raw receipt text and layout data from uploaded images.

**Files/modules likely to change:**

- New `rag/ocr.py`
- `requirements.txt`
- `.env.example`

**What to implement:**

- Add a small `DocumentIntelligenceOCR` wrapper around Azure Document Intelligence’s receipt/prebuilt model.
- Accept image bytes or a temporary file path.
- Return a simple internal result containing:
  - Raw extracted text.
  - Recognized fields when available.
  - Line items and bounding/layout information when available.
  - OCR confidence values where provided.
- Translate Azure SDK errors into clear application-level errors for the UI.
- Do not persist the original image in the MVP unless explicitly required; optionally store a content hash for deduplication.

**Why it is needed:**

OCR is the first receipt-specific replacement for `PDFReader`. Keeping it in its own module makes the Azure dependency testable and prevents cloud SDK details from leaking into the pipeline or UI.

## Phase 3: Normalize and Tidy OCR Output

**Goal:** Convert inconsistent OCR output into a validated receipt structure.

**Files/modules likely to change:**

- New `rag/normalization.py`
- New or expanded `prompt.py`
- `llm.py`
- `requirements.txt`

**What to implement:**

- Add an `AzureOpenAILLM` implementation compatible with the existing `BaseLLM` abstraction.
- Add a normalization method that sends OCR text and extracted fields to Azure OpenAI.
- Require structured JSON output with a small schema, for example:
  - `merchant_name`
  - `receipt_date`
  - `currency`
  - `subtotal`
  - `tax`
  - `total`
  - `items`
- Each item should include:
  - `name`
  - `quantity`
  - `unit_price`
  - `line_total`
  - Optional `category`
- Validate and coerce the response before storage.
- Normalize dates to ISO format and amounts to numeric decimal-compatible values.
- Preserve raw OCR text for troubleshooting, but treat normalized fields as the application contract.
- Add retry and failure handling without recursively retrying indefinitely.

**Why it is needed:**

OCR output is not reliable enough for direct querying. Normalization establishes one consistent receipt model for SQL queries, vector indexing, and answer generation.

## Phase 4: Add Structured Receipt Storage

**Goal:** Persist receipt facts and line items in a minimal relational database.

**Files/modules likely to change:**

- New `rag/storage.py` or `rag/database.py`
- New `rag/models.py` if dataclasses are useful
- New `rag/receipt_service.py`
- `.gitignore`
- `README.md`

**What to implement:**

Use SQLite for the MVP with two primary tables:

- `receipts`
  - ID
  - merchant
  - receipt date
  - currency
  - subtotal
  - tax
  - total
  - raw OCR text
  - normalized JSON
  - created timestamp
- `receipt_items`
  - ID
  - receipt ID
  - item name
  - normalized item name
  - quantity
  - unit price
  - line total
  - category

Add a small repository/service layer with functions to:

- Initialize the schema.
- Insert a normalized receipt and its items transactionally.
- List receipts.
- Query items by date range.
- Calculate totals by category/date range.
- Find merchants or items matching exact/normalized names.

Avoid introducing an ORM unless the project already adopts one. Python’s built-in `sqlite3` module is sufficient for this application.

**Why it is needed:**

Questions involving dates, totals, quantities, and categories should be answered deterministically from structured data rather than inferred from embeddings or an LLM.

## Phase 5: Implement the Local Vector Store

**Goal:** Add a simple file-backed semantic index without a high-level vector database.

**Files/modules likely to change:**

- New `rag/vector_store.py`
- `retrieval.py`
- `llm.py` or a small embedding wrapper
- `requirements.txt`

**What to implement:**

- Add an embedding provider using Azure OpenAI embeddings, or the repository’s existing sentence-transformers dependency if local embeddings are preferred.
- Store records in a JSON file or SQLite table containing:
  - Document ID.
  - Receipt/item metadata.
  - Text used for embedding.
  - Embedding vector.
- Implement manually:
  - Vector normalization.
  - Dot product.
  - Vector magnitude.
  - Cosine similarity.
  - Top-k sorting.
- Add `ingest()` and `retrieve()` methods compatible with the existing `BaseRetrieval` shape where practical.
- Index one or more searchable documents per receipt, such as:
  - Merchant plus date and total.
  - One document per item.
  - Optional combined receipt text.
- Rebuild or update the index after successful receipt persistence.
- Handle empty vectors, dimension mismatches, and an empty index explicitly.

Do not add FAISS, Chroma, Pinecone, Qdrant, or another vector database in the MVP.

**Why it is needed:**

The user explicitly requires a local vector database implemented from scratch. Keeping it as a small retrieval module preserves the repository’s existing retrieval abstraction while making cosine similarity visible and maintainable.

## Phase 6: Add Query Routing and Answering

**Goal:** Answer receipt questions with the correct source of truth.

**Files/modules likely to change:**

- New `rag/query_service.py`
- `pipeline.py`
- `prompt.py`
- `retrieval.py`
- Streamlit UI module

**What to implement:**

Add a query service that classifies questions into two practical paths:

### Structured database path

Use SQLite for questions involving:

- Explicit dates or date ranges.
- Totals and sums.
- Food/category filtering.
- Quantities.
- Exact merchant/item lookups when normalized SQL matching is sufficient.

Examples:

- “What food did I buy yesterday?”
- “Give me total expenses for food on 20 June.”

The service should parse the date/category intent, execute parameterized SQL, and format the result without asking the LLM to calculate totals.

### Vector retrieval path

Use vector similarity for questions involving:

- Fuzzy item names.
- Natural-language descriptions.
- Store/item associations.
- Queries where the user does not use the exact normalized name.

Example:

- “Where did I buy hamburger from last 7 day?”

Retrieve the top matching item or receipt records, then provide the results to Azure OpenAI only for concise wording and ambiguity handling. The LLM must not invent facts absent from retrieved records.

### Pipeline integration

Either:

- Extend `SimpleRAGPipeline` with a receipt-aware mode, or
- Add a separate `ReceiptQueryPipeline` alongside it.

The second option is cleaner because the existing pipeline assumes generic text chunks and always generates an LLM answer. The new pipeline can reuse `Answer` and retrieval interfaces without changing existing PDF behavior.

**Why it is needed:**

SQL is reliable for arithmetic and date filtering; vector retrieval is useful for semantic matching. Explicit routing prevents inaccurate LLM-generated totals and keeps the implementation understandable.

## Phase 7: Replace the Demo UI with Receipt Workflow

**Goal:** Provide the complete user-facing flow.

**Files/modules likely to change:**

- `simple_rag_bm25_ollama_ui.py`, preferably renamed to a receipt-specific entry point
- New `examples/receipt_app.py` if preserving the original example
- `README.md`
- `.gitignore`

**What to implement:**

The UI should support:

1. Upload receipt image.
2. Run OCR.
3. Show a preview of extracted/normalized receipt data.
4. Allow the user to confirm or retry normalization.
5. Save the receipt.
6. Index its searchable text and embeddings.
7. Ask questions.
8. Display answers and optionally the matching receipt/item records.

Use Streamlit for the MVP because the repository already contains a Streamlit example. Do not introduce React, a separate API server, or a frontend build system unless the UI requirements later demand it.

**Why it is needed:**

This turns the existing demonstration UI into the complete application workflow while reusing the project’s current framework and execution model.

## Phase 8: Containerize the Application

**Goal:** Run the receipt app locally in Docker.

**Files/modules likely to change:**

- New `Dockerfile`
- New `docker-compose.yml`
- `.dockerignore`
- `requirements.txt`
- `.env.example`
- `README.md`

**What to implement:**

- Use a Python base image.
- Install Python dependencies.
- Copy the `rag` package and receipt app.
- Expose Streamlit’s port.
- Run the app with a non-development command.
- Mount a local data directory for:
  - SQLite database.
  - Vector index.
  - Optional uploaded files.
- Pass Azure configuration through environment variables.
- Add a health-oriented smoke command or at least verify the Streamlit process starts.

Keep Docker Compose to one application container with local file persistence. Azure services remain external dependencies.

**Why it is needed:**

The MVP needs reproducible local startup without introducing extra containers for services that are not required by the design.

## Phase 9: Add Tests and CI/CD

**Goal:** Make the application maintainable and automatically verifiable.

**Files/modules likely to change:**

- New tests under `test`
- New `.github/workflows/ci.yml`
- `pyproject.toml`
- `requirements.txt`
- `README.md`

**What to implement:**

Add focused tests for:

- Receipt normalization validation using mocked Azure OpenAI responses.
- OCR adapter behavior using mocked Document Intelligence responses.
- SQLite schema and transactional receipt insertion.
- Date-range and category aggregation queries.
- Manual cosine similarity, including:
  - Identical vectors.
  - Orthogonal vectors.
  - Zero vectors.
  - Top-k ordering.
- Query routing between SQL and vector paths.
- A minimal application import/startup check.

Mock Azure services in CI; do not require cloud credentials for pull requests.

GitHub Actions should:

- Install a supported Python version.
- Install dependencies.
- Run formatting/linting if configured.
- Run unit tests.
- Build the Docker image.
- Optionally run a container startup smoke test.

**Why it is needed:**

The highest-risk logic is normalization, financial aggregation, and vector math. These can all be tested locally without Azure access.

## Minimum File/Module Change Summary

Add:

- `rag/ocr.py`
- `rag/normalization.py`
- `rag/database.py` or `rag/storage.py`
- `rag/vector_store.py`
- `rag/query_service.py`
- Receipt-specific UI entry point
- Tests under `test`
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.github/workflows/ci.yml`

Modify:

- `llm.py`
- `prompt.py`
- `pipeline.py` only if sharing/reusing pipeline types
- `requirements.txt`
- `setup.py`
- `.env.example`
- `.gitignore`
- `README.md`

Keep initially unchanged:

- `rerank.py`
- `text_utils.py`
- Existing PDF example and `PDFReader`, unless the repository is intentionally being converted completely from PDF RAG to receipts.

## Recommended MVP Sequence

1. Add configuration and a receipt-focused Streamlit shell.
2. Implement and mock-test Azure Document Intelligence OCR.
3. Implement normalized receipt schema and Azure OpenAI normalization.
4. Add SQLite persistence and deterministic aggregation queries.
5. Implement manual vector storage and cosine similarity.
6. Add query routing and answer formatting.
7. Connect the full upload-to-query UI flow.
8. Add Docker and local persistent volumes.
9. Add unit tests, GitHub Actions, and documentation updates.

This sequence ensures that the app can first ingest and save receipts before semantic retrieval is introduced. The structured database becomes the reliable foundation, while vector retrieval is added only for questions that benefit from fuzzy matching.

Created 10 todos