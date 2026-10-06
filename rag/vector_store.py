import json
import math
import re
from pathlib import Path
from typing import Any, Callable


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


class LocalVectorStore:
    def __init__(self, path: str = "vectors.json"):
        self.path = Path(path)
        self.records: list[dict[str, Any]] = json.loads(self.path.read_text()) if self.path.exists() else []

    def ingest(self, text: str, metadata: dict[str, Any], embed: Callable[[str], list[float]]) -> None:
        self.records.append({"text": text, "metadata": metadata, "embedding": embed(text)})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.records))

    def retrieve(self, query: str, embed: Callable[[str], list[float]], top_k: int = 5) -> list[dict[str, Any]]:
        query_vector = embed(query)
        ranked = sorted(self.records, key=lambda record: cosine_similarity(query_vector, record["embedding"]), reverse=True)
        return [{**record, "score": cosine_similarity(query_vector, record["embedding"])} for record in ranked[:top_k]]


def word_embedding(text: str) -> list[float]:
    words = re.findall(r"[a-z0-9]+", text.casefold())
    vocabulary = sorted(set(words))
    return [float(words.count(word)) for word in vocabulary]