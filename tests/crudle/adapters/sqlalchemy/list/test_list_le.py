"""List filters: less-than-or-equal operator (`le`).

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — field__le, nested path / nested dict
- Value shapes — None, empty string, numbers, etc.

Note: there is no bare-field form for `le` (bare `field=value` is always `eq`).
Unlike `lt`, the boundary value itself matches.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import ArgumentError

from tests.models import Item, ItemList, ItemType, Tag

# ---------------------------------------------------------------------------
# Matches — when less-than-or-equal finds rows
# ---------------------------------------------------------------------------


class TestListLeMatches:
    def test_integer(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        item3 = Item.insert(db, name="Item 3", color="green", price=30)

        items = Item.list(db, price__le=20)

        assert set(items) == {item1, item2}
        assert item3 not in items

    def test_equal_boundary_included(self, db):
        """le includes equality; lt would exclude the boundary."""
        item_below = Item.insert(db, name="Item 1", color="red", price=10)
        item_boundary = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name="Item 3", color="green", price=30)

        assert set(Item.list(db, price__le=20)) == {item_below, item_boundary}
        assert Item.list(db, price__lt=20) == [item_below]

    def test_multiple_fields_anded(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="red", price=20)
        Item.insert(db, name="Item 3", color="blue", price=5)

        items = Item.list(db, color="red", price__le=15)

        assert items == [item1]
        assert item2 not in items


# ---------------------------------------------------------------------------
# Misses — when less-than-or-equal correctly returns empty
# ---------------------------------------------------------------------------


class TestListLeMisses:
    def test_all_rows_above_boundary(self, db):
        Item.insert(db, name="Item 1", color="red", price=25)
        Item.insert(db, name="Item 2", color="blue", price=30)

        assert Item.list(db, price__le=20) == []

    def test_partial_and_does_not_match(self, db):
        Item.insert(db, name="Item 1", color="red", price=30)

        assert Item.list(db, color="red", price__le=20) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __le and nested forms
# ---------------------------------------------------------------------------


class TestListLeSpellings:
    def test_nested_dotted_path(self, db):
        item_cheap = Item.insert(db, name="Item 1", color="red", price=10)
        item_expensive = Item.insert(db, name="Item 2", color="blue", price=30)
        list1 = ItemList.insert(db, name="List 1", items=[item_cheap, item_expensive])
        ItemList.insert(db, name="List 2", items=[item_expensive])

        lists = ItemList.list(db, **{"items.price__le": 20})

        assert lists == [list1]

    def test_nested_dict_filter(self, db):
        item_cheap = Item.insert(db, name="Item 1", color="red", price=10)
        item_expensive = Item.insert(db, name="Item 2", color="blue", price=30)
        list1 = ItemList.insert(db, name="List 1", items=[item_cheap, item_expensive])
        ItemList.insert(db, name="List 2", items=[item_expensive])

        lists = ItemList.list(db, filter={"items": {"price__le": 20}})

        assert lists == [list1]

    def test_nested_deep_dotted_path(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        list1 = ItemList.insert(db, name="List 1", items=[item1])
        list2 = ItemList.insert(db, name="List 2", items=[item2])
        Tag.insert(db, name="a-tag", items=[item1])
        Tag.insert(db, name="m", items=[item2])

        # tag name <= "m" → a-tag and exact "m"
        lists = ItemList.list(db, **{"items.tags.name__le": "m"})

        assert set(lists) == {list1, list2}

    def test_belongs_to_relationship(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        shirt = Item.insert(db, name="Shirt", color="blue", item_type=clothing)
        Item.insert(db, name="Phone", color="red", item_type=electronics)

        items = Item.list(db, **{"item_type.name__le": "Clothing"})

        assert items == [shirt]


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListLeValueShapes:
    def test_null_column_excluded(self, db):
        """price__le=20 excludes NULL (SQL three-valued logic)."""
        item_low = Item.insert(db, name="Item 1", color="red", price=10)
        item_boundary = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name="Item 3", color="green", price=None)

        items = Item.list(db, price__le=20)

        assert set(items) == {item_low, item_boundary}

    def test_none_filter_value_rejected(self, db):
        """price__le=None is not a valid SQL comparison."""
        Item.insert(db, name="Item 1", color="red", price=10)

        with pytest.raises(ArgumentError):
            Item.list(db, price__le=None)

    def test_empty_string(self, db):
        item_empty = Item.insert(db, name="", color="red", price=10)
        item_named = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name=None, color="green", price=30)

        # le includes "" itself; non-empty names are greater, so excluded; NULL excluded
        assert Item.list(db, name__le="") == [item_empty]
        assert item_named not in Item.list(db, name__le="")

    def test_string(self, db):
        item_blue = Item.insert(db, name="Item 1", color="blue", price=10)
        item_red = Item.insert(db, name="Item 2", color="red", price=20)
        item_m = Item.insert(db, name="Item 3", color="m", price=15)

        assert set(Item.list(db, color__le="m")) == {item_blue, item_m}
        assert item_red not in Item.list(db, color__le="m")

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        moment_naive = moment.replace(tzinfo=None)
        other_naive = other.replace(tzinfo=None)

        item1 = Item.insert(db, name="Item 1", color="red", created_at=moment_naive)
        item2 = Item.insert(db, name="Item 2", color="blue", created_at=other_naive)

        assert set(Item.list(db, created_at__le=other_naive)) == {item1, item2}
        assert Item.list(db, created_at__lt=other_naive) == [item1]
