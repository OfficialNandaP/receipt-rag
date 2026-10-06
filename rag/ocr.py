from dataclasses import dataclass
from typing import Any


@dataclass
class OCRResult:
    text: str
    fields: dict[str, Any]
    items: list[dict[str, Any]]


class DocumentIntelligenceOCR:
    def __init__(self, endpoint: str, key: str):
        if not endpoint or not key:
            raise ValueError("Document Intelligence endpoint and key are required")
        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError as error:
            raise ImportError("Install azure-ai-formrecognizer to use Azure OCR") from error
        self.client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    def analyze(self, image: bytes) -> OCRResult:
        try:
            poller = self.client.begin_analyze_document("prebuilt-receipt", image)
            result = poller.result()
        except Exception as error:
            raise RuntimeError(f"Receipt OCR failed: {error}") from error
        document = result.documents[0] if result.documents else None
        fields = document.fields if document else {}
        items = []
        for item in fields.get("Items").value or [] if fields.get("Items") else []:
            item_fields = item.value or {}
            items.append({name: field.value for name, field in item_fields.items()})
        return OCRResult(text="\n".join(line.content for page in result.pages for line in page.lines), fields=fields, items=items)