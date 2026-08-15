"""List filters: membership operator (`in`).

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — field__in, nested path / nested dict
- Value shapes — None, empty list, empty string, numbers, etc.

Note: there is no bare-field form for `in` (bare `field=value` is always `eq`).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import ArgumentError

from tests.models import Item, ItemList, ItemType, Tag


# ---------------------------------------------------------------------------
# Matches — when membership finds rows
# ---------------------------------------------------------------------------


class TestListInMatches:
    def test_string_list(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        item3 = Item.insert(db, name="Item 3", color="green", price=30)

        items = Item.list(db, color__in=["red", "blue"])

        assert set(items) == {item1, item2}
        assert item3 not in items

    def test_multiple_fields_anded(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="red", price=20)
        Item.insert(db, name="Item 3", color="blue", price=10)

        items = Item.list(db, color="red", price__in=[10, 30])

        assert items == [item1]
        assert item2 not in items


# ---------------------------------------------------------------------------
# Misses — when membership correctly returns empty
# ---------------------------------------------------------------------------


class TestListInMisses:
    def test_no_overlap(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)
        Item.insert(db, name="Item 2", color="blue", price=20)

        assert Item.list(db, color__in=["purple", "orange"]) == []

    def test_empty_list(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)

        assert Item.list(db, color__in=[]) == []

    def test_partial_and_does_not_match(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)

        assert Item.list(db, color="red", price__in=[99]) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __in and nested forms
# ---------------------------------------------------------------------------


class TestListInSpellings:
    def test_nested_dotted_path(self, db):
        item_red = Item.insert(db, name="Item 1", color="red")
        item_blue = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="List 1", items=[item_red, item_blue])
        ItemList.insert(db, name="List 2", items=[item_red])

        lists = ItemList.list(db, **{"items.color__in": ["blue", "green"]})

        assert lists == [list1]

    def test_nested_dict_filter(self, db):
        item_red = Item.insert(db, name="Item 1", color="red")
        item_blue = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="List 1", items=[item_red, item_blue])
        ItemList.insert(db, name="List 2", items=[item_red])

        lists = ItemList.list(db, filter={"items": {"color__in": ["blue", "green"]}})

        assert lists == [list1]

    def test_nested_deep_dotted_path(self, db):
        item1 = Item.insert(db, name="Item 1", color="red")
        item2 = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="List 1", items=[item1])
        ItemList.insert(db, name="List 2", items=[item2])
        Tag.insert(db, name="expensive", items=[item1])
        Tag.insert(db, name="cheap", items=[item2])

        lists = ItemList.list(db, **{"items.tags.name__in": ["expensive"]})

        assert lists == [list1]

    def test_belongs_to_relationship(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        phone = Item.insert(db, name="Phone", color="red", item_type=electronics)
        Item.insert(db, name="Shirt", color="blue", item_type=clothing)

        items = Item.list(db, **{"item_type.name__in": ["Electronics"]})

        assert items == [phone]


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListInValueShapes:
    def test_null_column_excluded(self, db):
        """NULL column is never IN (...), even with None in the list."""
        item_red = Item.insert(db, name="Item 1", color="red", price=10)
        Item.insert(db, name="Item 2", color=None, price=20)

        assert Item.list(db, color__in=["red", "blue"]) == [item_red]
        assert Item.list(db, color__in=["red", None]) == [item_red]

    def test_none_filter_value_rejected(self, db):
        """color__in=None is not a valid IN expression list."""
        Item.insert(db, name="Item 1", color="red", price=10)

        with pytest.raises(ArgumentError):
            Item.list(db, color__in=None)

    def test_empty_string(self, db):
        item_empty = Item.insert(db, name="", color="red", price=10)
        item_named = Item.insert(db, name="Item 2", color="blue", price=20)

        assert Item.list(db, name__in=[""]) == [item_empty]
        assert item_named not in Item.list(db, name__in=[""])

    def test_integer(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        item3 = Item.insert(db, name="Item 3", color="green", price=30)

        assert set(Item.list(db, price__in=[10, 30])) == {item1, item3}
        assert item2 not in Item.list(db, price__in=[10, 30])

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        moment_naive = moment.replace(tzinfo=None)
        other_naive = other.replace(tzinfo=None)

        item1 = Item.insert(db, name="Item 1", color="red", created_at=moment_naive)
        item2 = Item.insert(db, name="Item 2", color="blue", created_at=other_naive)

        assert Item.list(db, created_at__in=[moment_naive]) == [item1]
        assert item2 not in Item.list(db, created_at__in=[moment_naive])
