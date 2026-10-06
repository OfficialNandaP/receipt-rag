ANSWER_PROMPT = """Answer the following query using the provided context.
- Query: {query}
- Context: {context}
"""

RECEIPT_NORMALIZATION_PROMPT = """Normalize receipt OCR into JSON only.
Use only the supplied OCR data. Do not invent values. Use empty strings for unknown fields.
OCR text:
{ocr_text}
Recognized fields:
{fields_json}
Recognized items:
{items_json}

Return this schema exactly. Use an empty string for an unknown receipt_date; never invent a date.
{{"merchant_name":"","receipt_date":"","currency":"","subtotal":"0.00","tax":"0.00","total":"0.00","items":[{{"name":"","quantity":"1","unit_price":"0.00","line_total":"0.00","category":"other"}}]}}
"""

RECEIPT_ANSWER_PROMPT = """Answer the question using only the retrieved receipt records.
If the records do not support an answer, say that there is not enough information.
Never invent dates, merchants, products, quantities, or amounts.
Question: {query}
Retrieved records:
{context}
"""
