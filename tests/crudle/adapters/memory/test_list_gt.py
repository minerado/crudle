"""List filters: greater-than operator (`gt`) — Memory adapter.

Stress twin of tests/crudle/sqlalchemy/test_list_gt.py.
Same scenarios and sections; call shape is db.method(Model, ...).
Assertions compare by id because Memory returns copies.

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — field__gt, nested path / nested dict
- Value shapes — None, empty string, numbers, etc.

Note: there is no bare-field form for `gt` (bare `field=value` is always `eq`).
"""

from datetime import datetime, timezone

import pytest

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def _ids(rows):
    return {row.id for row in rows}


# ---------------------------------------------------------------------------
# Matches — when greater-than finds rows
# ---------------------------------------------------------------------------


class TestListGtMatches:
    def test_integer(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        item3 = db.insert(Item, name="Item 3", color="green", price=30)

        items = db.list(Item, price__gt=15)

        assert _ids(items) == {item2.id, item3.id}
        assert item1.id not in _ids(items)

    def test_multiple_fields_anded(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=30)

        items = db.list(Item, color="red", price__gt=15)

        assert _ids(items) == {item2.id}
        assert item1.id not in _ids(items)


# ---------------------------------------------------------------------------
# Misses — when greater-than correctly returns empty
# ---------------------------------------------------------------------------


class TestListGtMisses:
    def test_all_rows_not_greater(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="blue", price=15)

        assert db.list(Item, price__gt=15) == []

    def test_partial_and_does_not_match(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        assert db.list(Item, color="red", price__gt=15) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __gt and nested forms
# ---------------------------------------------------------------------------


class TestListGtSpellings:
    def test_nested_dotted_path(self, db):
        item_cheap = db.insert(Item, name="Item 1", color="red", price=10)
        item_expensive = db.insert(Item, name="Item 2", color="blue", price=20)
        list1 = db.insert(ItemList, name="List 1", items=[item_cheap, item_expensive])
        db.insert(ItemList, name="List 2", items=[item_cheap])

        lists = db.list(ItemList, **{"items.price__gt": 15})

        assert _ids(lists) == {list1.id}

    def test_nested_dict_filter(self, db):
        item_cheap = db.insert(Item, name="Item 1", color="red", price=10)
        item_expensive = db.insert(Item, name="Item 2", color="blue", price=20)
        list1 = db.insert(ItemList, name="List 1", items=[item_cheap, item_expensive])
        db.insert(ItemList, name="List 2", items=[item_cheap])

        lists = db.list(ItemList, filter={"items": {"price__gt": 15}})

        assert _ids(lists) == {list1.id}

    def test_nested_deep_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        list1 = db.insert(ItemList, name="List 1", items=[item1])
        list2 = db.insert(ItemList, name="List 2", items=[item2])
        db.insert(Tag, name="a-tag", items=[item1])
        db.insert(Tag, name="z-tag", items=[item2])

        lists = db.list(ItemList, **{"items.tags.name__gt": "m"})

        assert _ids(lists) == {list2.id}
        assert list1.id not in _ids(lists)

    def test_belongs_to_relationship(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        phone = db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Shirt", color="blue", item_type=clothing)

        items = db.list(Item, **{"item_type.name__gt": "D"})

        assert _ids(items) == {phone.id}


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListGtValueShapes:
    def test_null_column_excluded(self, db):
        """price__gt=15 excludes NULL (SQL three-valued logic)."""
        item_low = db.insert(Item, name="Item 1", color="red", price=10)
        item_high = db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name="Item 3", color="green", price=None)

        items = db.list(Item, price__gt=15)

        assert _ids(items) == {item_high.id}
        assert item_low.id not in _ids(items)

    def test_none_filter_value_rejected(self, db):
        """price__gt=None is rejected (SQLAlchemy ArgumentError parity)."""
        db.insert(Item, name="Item 1", color="red", price=10)

        with pytest.raises(Exception, match="None"):
            db.list(Item, price__gt=None)

    def test_empty_string(self, db):
        item_empty = db.insert(Item, name="", color="red", price=10)
        item_named = db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name=None, color="green", price=30)

        assert _ids(db.list(Item, name__gt="")) == {item_named.id}
        assert item_empty.id not in _ids(db.list(Item, name__gt=""))

    def test_string(self, db):
        item_blue = db.insert(Item, name="Item 1", color="blue", price=10)
        item_red = db.insert(Item, name="Item 2", color="red", price=20)

        assert _ids(db.list(Item, color__gt="m")) == {item_red.id}
        assert item_blue.id not in _ids(db.list(Item, color__gt="m"))

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        item1 = db.insert(Item, name="Item 1", color="red", created_at=moment)
        item2 = db.insert(Item, name="Item 2", color="blue", created_at=other)

        assert _ids(db.list(Item, created_at__gt=moment)) == {item2.id}
        assert item1.id not in _ids(db.list(Item, created_at__gt=moment))
