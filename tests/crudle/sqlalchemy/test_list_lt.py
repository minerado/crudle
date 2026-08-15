"""List filters: less-than operator (`lt`).

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — field__lt, nested path / nested dict
- Value shapes — None, empty string, numbers, etc.

Note: there is no bare-field form for `lt` (bare `field=value` is always `eq`).
Unlike `le`, the boundary value itself does not match.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import ArgumentError

from tests.models import Item, ItemList, ItemType, Tag


# ---------------------------------------------------------------------------
# Matches — when less-than finds rows
# ---------------------------------------------------------------------------


class TestListLtMatches:
    def test_integer(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        item3 = Item.insert(db, name="Item 3", color="green", price=30)

        items = Item.list(db, price__lt=25)

        assert set(items) == {item1, item2}
        assert item3 not in items

    def test_equal_boundary_excluded(self, db):
        """lt excludes equality; le would include the boundary."""
        item_below = Item.insert(db, name="Item 1", color="red", price=10)
        item_boundary = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name="Item 3", color="green", price=30)

        assert Item.list(db, price__lt=20) == [item_below]
        assert set(Item.list(db, price__le=20)) == {item_below, item_boundary}

    def test_multiple_fields_anded(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="red", price=20)
        Item.insert(db, name="Item 3", color="blue", price=5)

        items = Item.list(db, color="red", price__lt=15)

        assert items == [item1]
        assert item2 not in items


# ---------------------------------------------------------------------------
# Misses — when less-than correctly returns empty
# ---------------------------------------------------------------------------


class TestListLtMisses:
    def test_all_rows_not_less(self, db):
        Item.insert(db, name="Item 1", color="red", price=20)
        Item.insert(db, name="Item 2", color="blue", price=30)

        assert Item.list(db, price__lt=20) == []

    def test_partial_and_does_not_match(self, db):
        Item.insert(db, name="Item 1", color="red", price=30)

        assert Item.list(db, color="red", price__lt=25) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __lt and nested forms
# ---------------------------------------------------------------------------


class TestListLtSpellings:
    def test_nested_dotted_path(self, db):
        item_cheap = Item.insert(db, name="Item 1", color="red", price=10)
        item_expensive = Item.insert(db, name="Item 2", color="blue", price=30)
        list1 = ItemList.insert(db, name="List 1", items=[item_cheap, item_expensive])
        ItemList.insert(db, name="List 2", items=[item_expensive])

        lists = ItemList.list(db, **{"items.price__lt": 25})

        assert lists == [list1]

    def test_nested_dict_filter(self, db):
        item_cheap = Item.insert(db, name="Item 1", color="red", price=10)
        item_expensive = Item.insert(db, name="Item 2", color="blue", price=30)
        list1 = ItemList.insert(db, name="List 1", items=[item_cheap, item_expensive])
        ItemList.insert(db, name="List 2", items=[item_expensive])

        lists = ItemList.list(db, filter={"items": {"price__lt": 25}})

        assert lists == [list1]

    def test_nested_deep_dotted_path(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        list1 = ItemList.insert(db, name="List 1", items=[item1])
        list2 = ItemList.insert(db, name="List 2", items=[item2])
        Tag.insert(db, name="a-tag", items=[item1])
        Tag.insert(db, name="z-tag", items=[item2])

        # tag name < "m" → only list with a-tag (list1)
        lists = ItemList.list(db, **{"items.tags.name__lt": "m"})

        assert lists == [list1]
        assert list2 not in lists

    def test_belongs_to_relationship(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        shirt = Item.insert(db, name="Shirt", color="blue", item_type=clothing)
        Item.insert(db, name="Phone", color="red", item_type=electronics)

        items = Item.list(db, **{"item_type.name__lt": "D"})

        assert items == [shirt]


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListLtValueShapes:
    def test_null_column_excluded(self, db):
        """price__lt=25 excludes NULL (SQL three-valued logic)."""
        item_low = Item.insert(db, name="Item 1", color="red", price=10)
        item_high = Item.insert(db, name="Item 2", color="blue", price=30)
        Item.insert(db, name="Item 3", color="green", price=None)

        items = Item.list(db, price__lt=25)

        assert set(items) == {item_low}
        assert item_high not in items

    def test_none_filter_value_rejected(self, db):
        """price__lt=None is not a valid SQL comparison."""
        Item.insert(db, name="Item 1", color="red", price=10)

        with pytest.raises(ArgumentError):
            Item.list(db, price__lt=None)

    def test_empty_string(self, db):
        item_empty = Item.insert(db, name="", color="red", price=10)
        item_named = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name=None, color="green", price=30)

        # nothing is < ""; empty itself does not match; NULL excluded
        assert Item.list(db, name__lt="") == []
        assert item_empty not in Item.list(db, name__lt="")
        assert item_named not in Item.list(db, name__lt="")

    def test_string(self, db):
        item_blue = Item.insert(db, name="Item 1", color="blue", price=10)
        item_red = Item.insert(db, name="Item 2", color="red", price=20)

        # lexicographic: "blue" < "m", "red" is not
        assert Item.list(db, color__lt="m") == [item_blue]
        assert item_red not in Item.list(db, color__lt="m")

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        moment_naive = moment.replace(tzinfo=None)
        other_naive = other.replace(tzinfo=None)

        item1 = Item.insert(db, name="Item 1", color="red", created_at=moment_naive)
        item2 = Item.insert(db, name="Item 2", color="blue", created_at=other_naive)

        assert Item.list(db, created_at__lt=other_naive) == [item1]
        assert item2 not in Item.list(db, created_at__lt=other_naive)
