import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from .models import Receipt, ReceiptItem
from .prompt import RECEIPT_NORMALIZATION_PROMPT


def normalize_ocr_lines(text: str) -> Receipt:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 4:
        raise ValueError("OCR text needs merchant, item, quantity, and amount lines")
    amount_matches = re.findall(r"\d+(?:[.,]\d{1,2})", text)
    if not amount_matches:
        raise ValueError("OCR text does not contain a monetary amount")
    amount = _decimal(amount_matches[-1].replace(",", "."))
    quantity = Decimal("1")
    for value in amount_matches[:-1]:
        if Decimal(value.replace(",", ".")) == Decimal("1"):
            quantity = Decimal("1")
            break
    return Receipt(
        merchant_name=lines[0],
        receipt_date=date.today(),
        currency="",
        subtotal=amount,
        total=amount,
        items=[ReceiptItem(name=lines[1], quantity=quantity, unit_price=amount, line_total=amount)],
        raw_ocr_text=text,
    )


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid monetary value: {value!r}")


def normalize_receipt(data: str | dict[str, Any], raw_ocr_text: str = "") -> Receipt:
    if isinstance(data, str):
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return normalize_ocr_lines(data)
    else:
        payload = data
    try:
        receipt_date_value = str(payload.get("receipt_date") or "").strip()
        receipt_date = (
            date.fromisoformat(receipt_date_value)
            if receipt_date_value
            else date.today()
        )
        items = [
            ReceiptItem(
                name=str(item["name"]).strip(),
                quantity=Decimal(str(item.get("quantity", 1))),
                unit_price=_decimal(item.get("unit_price")),
                line_total=_decimal(item.get("line_total")),
                category=str(item.get("category", "other")).strip().lower(),
            )
            for item in payload.get("items", [])
        ]
        if any(not item.name for item in items):
            raise ValueError("Receipt item names cannot be empty")
        return Receipt(
            merchant_name=str(payload["merchant_name"]).strip(),
            receipt_date=receipt_date,
            currency=str(payload.get("currency", "")).strip(),
            subtotal=_decimal(payload.get("subtotal")),
            tax=_decimal(payload.get("tax")),
            total=_decimal(payload.get("total")),
            items=items,
            raw_ocr_text=raw_ocr_text,
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ValueError) and "Invalid isoformat" in str(error):
            raise ValueError(
                "Receipt date must use YYYY-MM-DD, or be left empty when unknown"
            ) from error
        raise ValueError(f"Missing receipt field: {error.args[0]}") from error


def normalize_with_azure_openai(
    ocr_text: str,
    ocr_fields: dict[str, Any],
    ocr_items: list[dict[str, Any]],
    llm: Any,
) -> Receipt:
    if not ocr_text.strip():
        raise ValueError("OCR text cannot be empty")
    prompt = RECEIPT_NORMALIZATION_PROMPT.format(
        ocr_text=ocr_text,
        fields_json=json.dumps(ocr_fields, default=str),
        items_json=json.dumps(ocr_items, default=str),
    )
    response = llm.generate(
        prompt,
        response_format={"type": "json_object"},
    )
    try:
        return normalize_receipt(_extract_json(response), raw_ocr_text=ocr_text)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("Azure OpenAI returned invalid receipt JSON") from error


def _extract_json(response: str) -> dict[str, Any]:
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I | re.S).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("No JSON object found in Azure OpenAI response")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Azure OpenAI response must be a JSON object")
    return value