from dataclasses import dataclass
from typing import List


@dataclass
class MemoryItem:
    target: str
    summary: str
    outcome: str


class RetrievalStore:
    def __init__(self):
        self.items: List[MemoryItem] = []

    def add(self, target: str, summary: str, outcome: str) -> None:
        self.items.append(MemoryItem(target=target, summary=summary, outcome=outcome))

    def query(self, text: str, limit: int = 3) -> List[MemoryItem]:
        lowered = text.lower()
        ranked = [item for item in self.items if lowered in item.target.lower() or lowered in item.summary.lower()]
        return ranked[:limit]
