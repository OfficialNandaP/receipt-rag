import re
import json
from datetime import date
from decimal import Decimal
from typing import Any, Callable

from .database import ReceiptDatabase
from .prompt import RECEIPT_ANSWER_PROMPT


class ReceiptQueryService:
    def __init__(self, database: ReceiptDatabase, vector_store: Any = None, llm: Any = None, embedder: Callable[[str], list[float]] | None = None):
        self.database = database
        self.vector_store = vector_store
        self.llm = llm
        self.embedder = embedder

    def answer(self, question: str) -> str:
        category_match = re.search(r"\b(food|drink|grocery|transport|other)\b", question, re.I)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", question)
        if category_match or date_match or re.search(r"\b(total|sum|expense|quantity|how many)\b", question, re.I):
            selected_date = date.fromisoformat(date_match.group(1)) if date_match else None
            rows = self.database.items(start=selected_date, end=selected_date, category=category_match.group(1) if category_match else None)
            if not rows:
                return "No matching receipt items found."
            total = sum((Decimal(str(row["line_total"])) for row in rows), Decimal("0"))
            names = ", ".join(row["name"] for row in rows)
            return f"Found {len(rows)} item(s) totaling {total:.2f}: {names}."
        if not self.vector_store or not self.llm or not self.embedder:
            return "Semantic search is not configured. Ask using a date, category, total, or expense term."
        records = self.vector_store.retrieve(question, self.embedder, top_k=5)
        if not records:
            return "No matching receipt records found."
        context = json.dumps(records, default=str)[:12000]
        prompt = RECEIPT_ANSWER_PROMPT.format(query=question, context=context)
        return self.llm.generate(prompt, temperature=0.0, max_tokens=400)