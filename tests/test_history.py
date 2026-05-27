from __future__ import annotations

import unittest

from clip_pocket.history import ClipboardHistory, HistoryChange, fingerprint


def make_history(
    retention_seconds: int | None = 60,
    min_text_length: int = 1,
    max_items: int = 100,
    max_text_length: int = 100_000,
    max_total_text_length: int = 5_000_000,
) -> ClipboardHistory:
    return ClipboardHistory(
        retention_seconds=retention_seconds,
        min_text_length=min_text_length,
        max_items=max_items,
        max_text_length=max_text_length,
        max_total_text_length=max_total_text_length,
    )


class ClipboardHistoryTest(unittest.TestCase):
    def test_ignores_empty_text(self) -> None:
        history = make_history()

        self.assertIs(history.add_or_refresh("", 0), HistoryChange.IGNORED)
        self.assertIs(history.add_or_refresh(" ", 0), HistoryChange.IGNORED)
        self.assertEqual(history.items, [])

    def test_adds_one_character_text(self) -> None:
        history = make_history()

        result = history.add_or_refresh("a", 0)

        self.assertIs(result, HistoryChange.ADDED)
        self.assertEqual([item.text for item in history.items], ["a"])

    def test_adds_new_text_to_top(self) -> None:
        history = make_history()

        history.add_or_refresh("りんご", 0)
        history.add_or_refresh("みかん", 1)

        self.assertEqual([item.text for item in history.items], ["みかん", "りんご"])

    def test_refreshes_duplicate_without_adding_new_item(self) -> None:
        history = make_history()

        history.add_or_refresh("りんご", 0)
        history.add_or_refresh("みかん", 1)
        result = history.add_or_refresh("りんご", 10)

        self.assertIs(result, HistoryChange.REFRESHED)
        self.assertEqual([item.text for item in history.items], ["りんご", "みかん"])
        self.assertEqual(len(history.items), 2)
        self.assertEqual(history.items[0].updated_at, 10)
        self.assertEqual(history.items[0].text_hash, fingerprint("りんご"))

    def test_delete_selected_indices(self) -> None:
        history = make_history()
        history.add_or_refresh("one", 0)
        history.add_or_refresh("two", 1)
        history.add_or_refresh("three", 2)

        history.delete_indices([0, 2])

        self.assertEqual([item.text for item in history.items], ["two"])

    def test_delete_indices_ignores_duplicates_and_out_of_range_values(self) -> None:
        history = make_history()
        history.add_or_refresh("one", 0)
        history.add_or_refresh("two", 1)

        history.delete_indices([0, 0, 10, -1])

        self.assertEqual([item.text for item in history.items], ["one"])

    def test_prunes_expired_items(self) -> None:
        history = make_history(retention_seconds=10)
        history.add_or_refresh("old", 0)
        history.add_or_refresh("fresh", 9)

        changed = history.prune(11)

        self.assertTrue(changed)
        self.assertEqual([item.text for item in history.items], ["fresh"])

    def test_unlimited_retention_does_not_prune_items(self) -> None:
        history = make_history(retention_seconds=None)
        history.add_or_refresh("old", 0)

        changed = history.prune(999_999)

        self.assertFalse(changed)
        self.assertEqual([item.text for item in history.items], ["old"])
        self.assertIsNone(history.remaining_minutes(history.items[0], 999_999))

    def test_ignores_text_longer_than_limit(self) -> None:
        history = make_history(max_text_length=4)

        self.assertIs(history.add_or_refresh("12345", 0), HistoryChange.IGNORED)
        self.assertEqual(history.items, [])

    def test_keeps_only_max_items(self) -> None:
        history = make_history(max_items=2)

        history.add_or_refresh("one", 0)
        history.add_or_refresh("two", 1)
        history.add_or_refresh("three", 2)

        self.assertEqual([item.text for item in history.items], ["three", "two"])

    def test_keeps_within_total_text_length_limit(self) -> None:
        history = make_history(max_total_text_length=8)

        history.add_or_refresh("abcd", 0)
        history.add_or_refresh("efgh", 1)
        history.add_or_refresh("ijkl", 2)

        self.assertEqual([item.text for item in history.items], ["ijkl", "efgh"])


if __name__ == "__main__":
    unittest.main()
