"""List filters: greater-than-or-equal operator (`ge`) — Memory adapter.

Stress twin of tests/crudle/sqlalchemy/test_list_ge.py.
Same scenarios and sections; call shape is db.method(Model, ...).
Assertions compare by id because Memory returns copies.

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — field__ge, nested path / nested dict
- Value shapes — None, empty string, numbers, etc.

Note: there is no bare-field form for `ge` (bare `field=value` is always `eq`).
Unlike `gt`, the boundary value itself matches.
"""

from datetime import datetime, timezone

import pytest

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def _ids(rows):
    return {row.id for row in rows}


# ---------------------------------------------------------------------------
# Matches — when greater-than-or-equal finds rows
# ---------------------------------------------------------------------------


class TestListGeMatches:
    def test_integer(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        item3 = db.insert(Item, name="Item 3", color="green", price=30)

        items = db.list(Item, price__ge=20)

        assert _ids(items) == {item2.id, item3.id}
        assert item1.id not in _ids(items)

    def test_equal_boundary_included(self, db):
        """ge includes equality; gt would exclude the boundary."""
        item_boundary = db.insert(Item, name="Item 1", color="red", price=20)
        item_above = db.insert(Item, name="Item 2", color="blue", price=30)
        db.insert(Item, name="Item 3", color="green", price=10)

        assert _ids(db.list(Item, price__ge=20)) == {item_boundary.id, item_above.id}
        assert _ids(db.list(Item, price__gt=20)) == {item_above.id}

    def test_multiple_fields_anded(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=30)

        items = db.list(Item, color="red", price__ge=20)

        assert _ids(items) == {item2.id}
        assert item1.id not in _ids(items)


# ---------------------------------------------------------------------------
# Misses — when greater-than-or-equal correctly returns empty
# ---------------------------------------------------------------------------


class TestListGeMisses:
    def test_all_rows_below_boundary(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="blue", price=15)

        assert db.list(Item, price__ge=20) == []

    def test_partial_and_does_not_match(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        assert db.list(Item, color="red", price__ge=20) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __ge and nested forms
# ---------------------------------------------------------------------------


class TestListGeSpellings:
    def test_nested_dotted_path(self, db):
        item_cheap = db.insert(Item, name="Item 1", color="red", price=10)
        item_boundary = db.insert(Item, name="Item 2", color="blue", price=20)
        list1 = db.insert(ItemList, name="List 1", items=[item_cheap, item_boundary])
        db.insert(ItemList, name="List 2", items=[item_cheap])

        lists = db.list(ItemList, **{"items.price__ge": 20})

        assert _ids(lists) == {list1.id}

    def test_nested_dict_filter(self, db):
        item_cheap = db.insert(Item, name="Item 1", color="red", price=10)
        item_boundary = db.insert(Item, name="Item 2", color="blue", price=20)
        list1 = db.insert(ItemList, name="List 1", items=[item_cheap, item_boundary])
        db.insert(ItemList, name="List 2", items=[item_cheap])

        lists = db.list(ItemList, filter={"items": {"price__ge": 20}})

        assert _ids(lists) == {list1.id}

    def test_nested_deep_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        list1 = db.insert(ItemList, name="List 1", items=[item1])
        list2 = db.insert(ItemList, name="List 2", items=[item2])
        db.insert(Tag, name="a-tag", items=[item1])
        db.insert(Tag, name="m-tag", items=[item2])

        lists = db.list(ItemList, **{"items.tags.name__ge": "m"})

        assert _ids(lists) == {list2.id}
        assert list1.id not in _ids(lists)

    def test_belongs_to_relationship(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        phone = db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Shirt", color="blue", item_type=clothing)

        items = db.list(Item, **{"item_type.name__ge": "Electronics"})

        assert _ids(items) == {phone.id}


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListGeValueShapes:
    def test_null_column_excluded(self, db):
        """price__ge=20 excludes NULL (SQL three-valued logic)."""
        item_low = db.insert(Item, name="Item 1", color="red", price=10)
        item_boundary = db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name="Item 3", color="green", price=None)

        items = db.list(Item, price__ge=20)

        assert _ids(items) == {item_boundary.id}
        assert item_low.id not in _ids(items)

    def test_none_filter_value_rejected(self, db):
        """price__ge=None is rejected (SQLAlchemy ArgumentError parity)."""
        db.insert(Item, name="Item 1", color="red", price=10)

        with pytest.raises(Exception, match="None"):
            db.list(Item, price__ge=None)

    def test_empty_string(self, db):
        item_empty = db.insert(Item, name="", color="red", price=10)
        item_named = db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name=None, color="green", price=30)

        assert _ids(db.list(Item, name__ge="")) == {item_empty.id, item_named.id}

    def test_string(self, db):
        item_blue = db.insert(Item, name="Item 1", color="blue", price=10)
        item_red = db.insert(Item, name="Item 2", color="red", price=20)
        item_m = db.insert(Item, name="Item 3", color="m", price=15)

        assert _ids(db.list(Item, color__ge="m")) == {item_red.id, item_m.id}
        assert item_blue.id not in _ids(db.list(Item, color__ge="m"))

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        item1 = db.insert(Item, name="Item 1", color="red", created_at=moment)
        item2 = db.insert(Item, name="Item 2", color="blue", created_at=other)

        assert _ids(db.list(Item, created_at__ge=moment)) == {item1.id, item2.id}
        assert _ids(db.list(Item, created_at__gt=moment)) == {item2.id}
