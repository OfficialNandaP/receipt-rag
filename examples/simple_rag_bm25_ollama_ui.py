import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

# Streamlit executes scripts from their directory, so add the repository root
# explicitly before importing the local rag package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.database import ReceiptDatabase
from rag.llm import AzureOpenAILLM
from rag.normalization import normalize_receipt
from rag.normalization import normalize_with_azure_openai
from rag.ocr import DocumentIntelligenceOCR
from rag.query_service import ReceiptQueryService
from rag.vector_store import LocalVectorStore, word_embedding

load_dotenv()
st.set_page_config(page_title="Receipt RAG", page_icon="Receipt")
st.title("Receipt RAG")

database = ReceiptDatabase(os.getenv("RECEIPT_DB_PATH", "/data/receipts.db"))
vector_store = LocalVectorStore(os.getenv("RECEIPT_VECTOR_PATH", "/data/vectors.json"))
try:
    llm = AzureOpenAILLM()
except (ImportError, ValueError):
    llm = None
uploaded_file = st.file_uploader("Upload a receipt image", type=["png", "jpg", "jpeg", "webp"])
ocr_text = st.text_area("Receipt JSON or OCR text", value=st.session_state.get("normalized_json", ""))

if uploaded_file and st.button("Extract receipt"):
    try:
        endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("DOCUMENT_INTELLIGENCE_KEY")
        if not endpoint or not key:
            raise ValueError("Set DOCUMENT_INTELLIGENCE_ENDPOINT and DOCUMENT_INTELLIGENCE_KEY in .env")
        result = DocumentIntelligenceOCR(endpoint, key).analyze(uploaded_file.getvalue())
        st.text_area("Extracted OCR text", result.text, height=180)
        st.session_state.ocr_text = result.text
        if llm:
            receipt = normalize_with_azure_openai(result.text, result.fields, result.items, llm)
            st.session_state.normalized_json = str(receipt.to_dict()).replace("'", '"')
        else:
            st.session_state.normalized_json = result.text
        st.info("OCR succeeded. Review the extracted text, then save it below.")
    except (ImportError, RuntimeError, TypeError, ValueError) as error:
        st.error(str(error))

if st.button("Save normalized JSON"):
    try:
        if not ocr_text.strip():
            raise ValueError("Provide receipt JSON or OCR text before saving.")
        receipt = normalize_receipt(ocr_text, raw_ocr_text=ocr_text)
        receipt_id = database.insert_receipt(receipt)
        vector_store.ingest(
            f"{receipt.merchant_name} {receipt.receipt_date} {receipt.total} "
            + " ".join(item.name for item in receipt.items),
            {"receipt_id": receipt_id, "merchant": receipt.merchant_name, "date": receipt.receipt_date.isoformat(), "total": str(receipt.total)},
            word_embedding,
        )
        st.success(f"Receipt saved with ID {receipt_id}.")
    except (TypeError, ValueError) as error:
        st.error(str(error))

# Ask questions visible only after ingesting PDF file
st.header("Ask Questions")
query = st.text_input("Your question")
if st.button("Ask") and query:
    st.write(ReceiptQueryService(database, vector_store, llm, word_embedding).answer(query))
