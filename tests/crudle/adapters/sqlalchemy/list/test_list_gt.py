"""List filters: greater-than operator (`gt`).

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — field__gt, nested path / nested dict
- Value shapes — None, empty string, numbers, etc.

Note: there is no bare-field form for `gt` (bare `field=value` is always `eq`).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import ArgumentError

from tests.models import Item, ItemList, ItemType, Tag


# ---------------------------------------------------------------------------
# Matches — when greater-than finds rows
# ---------------------------------------------------------------------------


class TestListGtMatches:
    def test_integer(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        item3 = Item.insert(db, name="Item 3", color="green", price=30)

        items = Item.list(db, price__gt=15)

        assert set(items) == {item2, item3}
        assert item1 not in items

    def test_multiple_fields_anded(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="red", price=20)
        Item.insert(db, name="Item 3", color="blue", price=30)

        # red AND price > 15 → only item2
        items = Item.list(db, color="red", price__gt=15)

        assert items == [item2]
        assert item1 not in items


# ---------------------------------------------------------------------------
# Misses — when greater-than correctly returns empty
# ---------------------------------------------------------------------------


class TestListGtMisses:
    def test_all_rows_not_greater(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)
        Item.insert(db, name="Item 2", color="blue", price=15)

        assert Item.list(db, price__gt=15) == []

    def test_partial_and_does_not_match(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)

        # color matches but price__gt cannot
        assert Item.list(db, color="red", price__gt=15) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __gt and nested forms
# ---------------------------------------------------------------------------


class TestListGtSpellings:
    def test_nested_dotted_path(self, db):
        item_cheap = Item.insert(db, name="Item 1", color="red", price=10)
        item_expensive = Item.insert(db, name="Item 2", color="blue", price=20)
        list1 = ItemList.insert(db, name="List 1", items=[item_cheap, item_expensive])
        ItemList.insert(db, name="List 2", items=[item_cheap])

        lists = ItemList.list(db, **{"items.price__gt": 15})

        assert lists == [list1]

    def test_nested_dict_filter(self, db):
        item_cheap = Item.insert(db, name="Item 1", color="red", price=10)
        item_expensive = Item.insert(db, name="Item 2", color="blue", price=20)
        list1 = ItemList.insert(db, name="List 1", items=[item_cheap, item_expensive])
        ItemList.insert(db, name="List 2", items=[item_cheap])

        lists = ItemList.list(db, filter={"items": {"price__gt": 15}})

        assert lists == [list1]

    def test_nested_deep_dotted_path(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        list1 = ItemList.insert(db, name="List 1", items=[item1])
        list2 = ItemList.insert(db, name="List 2", items=[item2])
        Tag.insert(db, name="a-tag", items=[item1])
        Tag.insert(db, name="z-tag", items=[item2])

        # tag name > "m" → only list with z-tag (list2); list1 has a-tag
        lists = ItemList.list(db, **{"items.tags.name__gt": "m"})

        assert lists == [list2]
        assert list1 not in lists

    def test_belongs_to_relationship(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        phone = Item.insert(db, name="Phone", color="red", item_type=electronics)
        Item.insert(db, name="Shirt", color="blue", item_type=clothing)

        items = Item.list(db, **{"item_type.name__gt": "D"})

        assert items == [phone]


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListGtValueShapes:
    def test_null_column_excluded(self, db):
        """price__gt=15 excludes NULL (SQL three-valued logic)."""
        item_low = Item.insert(db, name="Item 1", color="red", price=10)
        item_high = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name="Item 3", color="green", price=None)

        items = Item.list(db, price__gt=15)

        assert set(items) == {item_high}
        assert item_low not in items

    def test_none_filter_value_rejected(self, db):
        """price__gt=None is not a valid SQL comparison."""
        Item.insert(db, name="Item 1", color="red", price=10)

        with pytest.raises(ArgumentError):
            Item.list(db, price__gt=None)

    def test_empty_string(self, db):
        item_empty = Item.insert(db, name="", color="red", price=10)
        item_named = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name=None, color="green", price=30)

        assert Item.list(db, name__gt="") == [item_named]
        assert item_empty not in Item.list(db, name__gt="")

    def test_string(self, db):
        item_blue = Item.insert(db, name="Item 1", color="blue", price=10)
        item_red = Item.insert(db, name="Item 2", color="red", price=20)

        # lexicographic: "red" > "m", "blue" is not
        assert Item.list(db, color__gt="m") == [item_red]
        assert item_blue not in Item.list(db, color__gt="m")

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        moment_naive = moment.replace(tzinfo=None)
        other_naive = other.replace(tzinfo=None)

        item1 = Item.insert(db, name="Item 1", color="red", created_at=moment_naive)
        item2 = Item.insert(db, name="Item 2", color="blue", created_at=other_naive)

        assert Item.list(db, created_at__gt=moment_naive) == [item2]
        assert item1 not in Item.list(db, created_at__gt=moment_naive)
