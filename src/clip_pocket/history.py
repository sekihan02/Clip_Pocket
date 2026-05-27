from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from math import inf


class HistoryChange(Enum):
    IGNORED = auto()
    ADDED = auto()
    REFRESHED = auto()


@dataclass
class ClipboardItem:
    text: str
    created_at: float
    updated_at: float

    def expires_at(self, retention_seconds: int | None) -> float:
        if retention_seconds is None:
            return inf
        return self.updated_at + retention_seconds


class ClipboardHistory:
    def __init__(
        self,
        retention_seconds: int | None,
        min_text_length: int,
        max_items: int,
        max_text_length: int,
    ) -> None:
        self.retention_seconds = retention_seconds
        self.min_text_length = min_text_length
        self.max_items = max_items
        self.max_text_length = max_text_length
        self.items: list[ClipboardItem] = []

    def add_or_refresh(self, text: str, now: float) -> HistoryChange:
        if len(text.strip()) < self.min_text_length:
            return HistoryChange.IGNORED
        if len(text) > self.max_text_length:
            return HistoryChange.IGNORED

        duplicate_index = self.find_index(text)
        if duplicate_index is not None:
            self.touch(duplicate_index, now)
            self.prune(now)
            return HistoryChange.REFRESHED

        self.items.insert(0, ClipboardItem(text=text, created_at=now, updated_at=now))
        self.prune(now)
        self.enforce_max_items()
        return HistoryChange.ADDED

    def touch(self, index: int, now: float) -> int:
        item = self.items.pop(index)
        item.updated_at = now
        self.items.insert(0, item)
        return 0

    def delete_indices(self, indices: list[int]) -> None:
        for index in sorted(set(indices), reverse=True):
            if 0 <= index < len(self.items):
                del self.items[index]

    def prune(self, now: float) -> bool:
        if self.retention_seconds is None:
            return False

        before = len(self.items)
        self.items = [
            item
            for item in self.items
            if item.expires_at(self.retention_seconds) > now
        ]
        return len(self.items) != before

    def enforce_max_items(self) -> bool:
        before = len(self.items)
        del self.items[self.max_items :]
        return len(self.items) != before

    def find_index(self, text: str) -> int | None:
        for index, item in enumerate(self.items):
            if item.text == text:
                return index
        return None

    def remaining_minutes(self, item: ClipboardItem, now: float) -> int | None:
        if self.retention_seconds is None:
            return None
        seconds = max(0, int(item.expires_at(self.retention_seconds) - now))
        return seconds // 60
