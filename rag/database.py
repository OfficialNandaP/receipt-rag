import json
import sqlite3
from datetime import date
from decimal import Decimal
from typing import Any

from .models import Receipt


class ReceiptDatabase:
    def __init__(self, path: str = "receipts.db"):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, merchant TEXT NOT NULL,
                receipt_date TEXT NOT NULL, currency TEXT, subtotal NUMERIC,
                tax NUMERIC, total NUMERIC, raw_ocr_text TEXT, normalized_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS receipt_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, receipt_id INTEGER NOT NULL,
                name TEXT NOT NULL, normalized_name TEXT NOT NULL, quantity NUMERIC,
                unit_price NUMERIC, line_total NUMERIC, category TEXT,
                FOREIGN KEY(receipt_id) REFERENCES receipts(id)
            );
            """
        )
        self.connection.commit()

    def insert_receipt(self, receipt: Receipt) -> int:
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO receipts (merchant, receipt_date, currency, subtotal, tax, total, raw_ocr_text, normalized_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (receipt.merchant_name, receipt.receipt_date.isoformat(), receipt.currency,
                 str(receipt.subtotal), str(receipt.tax), str(receipt.total), receipt.raw_ocr_text,
                 json.dumps(receipt.to_dict())),
            )
            receipt_id = int(cursor.lastrowid)
            self.connection.executemany(
                "INSERT INTO receipt_items (receipt_id, name, normalized_name, quantity, unit_price, line_total, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(receipt_id, item.name, item.name.casefold(), str(item.quantity), str(item.unit_price), str(item.line_total), item.category) for item in receipt.items],
            )
        return receipt_id

    def items(self, start: date | None = None, end: date | None = None, category: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT i.*, r.merchant, r.receipt_date FROM receipt_items i JOIN receipts r ON r.id = i.receipt_id WHERE 1=1"
        params: list[Any] = []
        if start:
            query += " AND r.receipt_date >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND r.receipt_date <= ?"
            params.append(end.isoformat())
        if category:
            query += " AND lower(i.category) = lower(?)"
            params.append(category)
        return [dict(row) for row in self.connection.execute(query, params)]

    def close(self) -> None:
        self.connection.close()