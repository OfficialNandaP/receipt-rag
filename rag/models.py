from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass
class ReceiptItem:
    name: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    line_total: Decimal = Decimal("0")
    category: str = "other"

    def to_dict(self) -> dict[str, Any]:
        values = asdict(self)
        return {key: (str(value) if isinstance(value, Decimal) else value) for key, value in values.items()}


@dataclass
class Receipt:
    merchant_name: str
    receipt_date: date
    currency: str = ""
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    items: list[ReceiptItem] = field(default_factory=list)
    raw_ocr_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "merchant_name": self.merchant_name,
            "receipt_date": self.receipt_date.isoformat(),
            "currency": self.currency,
            "subtotal": str(self.subtotal),
            "tax": str(self.tax),
            "total": str(self.total),
            "items": [item.to_dict() for item in self.items],
        }