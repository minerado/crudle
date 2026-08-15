"""List filters: less-than operator (`lt`) — Memory adapter.

Stress twin of tests/crudle/sqlalchemy/test_list_lt.py.
Same scenarios and sections; call shape is db.method(Model, ...).
Assertions compare by id because Memory returns copies.

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

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def _ids(rows):
    return {row.id for row in rows}


# ---------------------------------------------------------------------------
# Matches — when less-than finds rows
# ---------------------------------------------------------------------------


class TestListLtMatches:
    def test_integer(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        item3 = db.insert(Item, name="Item 3", color="green", price=30)

        items = db.list(Item, price__lt=25)

        assert _ids(items) == {item1.id, item2.id}
        assert item3.id not in _ids(items)

    def test_equal_boundary_excluded(self, db):
        """lt excludes equality; le would include the boundary."""
        item_below = db.insert(Item, name="Item 1", color="red", price=10)
        item_boundary = db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name="Item 3", color="green", price=30)

        assert _ids(db.list(Item, price__lt=20)) == {item_below.id}
        assert _ids(db.list(Item, price__le=20)) == {item_below.id, item_boundary.id}

    def test_multiple_fields_anded(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=5)

        items = db.list(Item, color="red", price__lt=15)

        assert _ids(items) == {item1.id}
        assert item2.id not in _ids(items)


# ---------------------------------------------------------------------------
# Misses — when less-than correctly returns empty
# ---------------------------------------------------------------------------


class TestListLtMisses:
    def test_all_rows_not_less(self, db):
        db.insert(Item, name="Item 1", color="red", price=20)
        db.insert(Item, name="Item 2", color="blue", price=30)

        assert db.list(Item, price__lt=20) == []

    def test_partial_and_does_not_match(self, db):
        db.insert(Item, name="Item 1", color="red", price=30)

        assert db.list(Item, color="red", price__lt=25) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __lt and nested forms
# ---------------------------------------------------------------------------


class TestListLtSpellings:
    def test_nested_dotted_path(self, db):
        item_cheap = db.insert(Item, name="Item 1", color="red", price=10)
        item_expensive = db.insert(Item, name="Item 2", color="blue", price=30)
        list1 = db.insert(ItemList, name="List 1", items=[item_cheap, item_expensive])
        db.insert(ItemList, name="List 2", items=[item_expensive])

        lists = db.list(ItemList, **{"items.price__lt": 25})

        assert _ids(lists) == {list1.id}

    def test_nested_dict_filter(self, db):
        item_cheap = db.insert(Item, name="Item 1", color="red", price=10)
        item_expensive = db.insert(Item, name="Item 2", color="blue", price=30)
        list1 = db.insert(ItemList, name="List 1", items=[item_cheap, item_expensive])
        db.insert(ItemList, name="List 2", items=[item_expensive])

        lists = db.list(ItemList, filter={"items": {"price__lt": 25}})

        assert _ids(lists) == {list1.id}

    def test_nested_deep_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        list1 = db.insert(ItemList, name="List 1", items=[item1])
        list2 = db.insert(ItemList, name="List 2", items=[item2])
        db.insert(Tag, name="a-tag", items=[item1])
        db.insert(Tag, name="z-tag", items=[item2])

        lists = db.list(ItemList, **{"items.tags.name__lt": "m"})

        assert _ids(lists) == {list1.id}
        assert list2.id not in _ids(lists)

    def test_belongs_to_relationship(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        shirt = db.insert(Item, name="Shirt", color="blue", item_type=clothing)
        db.insert(Item, name="Phone", color="red", item_type=electronics)

        items = db.list(Item, **{"item_type.name__lt": "D"})

        assert _ids(items) == {shirt.id}


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListLtValueShapes:
    def test_null_column_excluded(self, db):
        """price__lt=25 excludes NULL (SQL three-valued logic)."""
        item_low = db.insert(Item, name="Item 1", color="red", price=10)
        item_high = db.insert(Item, name="Item 2", color="blue", price=30)
        db.insert(Item, name="Item 3", color="green", price=None)

        items = db.list(Item, price__lt=25)

        assert _ids(items) == {item_low.id}
        assert item_high.id not in _ids(items)

    def test_none_filter_value_rejected(self, db):
        """price__lt=None is rejected (SQLAlchemy ArgumentError parity)."""
        db.insert(Item, name="Item 1", color="red", price=10)

        with pytest.raises(Exception, match="None"):
            db.list(Item, price__lt=None)

    def test_empty_string(self, db):
        item_empty = db.insert(Item, name="", color="red", price=10)
        item_named = db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name=None, color="green", price=30)

        assert db.list(Item, name__lt="") == []
        assert item_empty.id not in _ids(db.list(Item, name__lt=""))
        assert item_named.id not in _ids(db.list(Item, name__lt=""))

    def test_string(self, db):
        item_blue = db.insert(Item, name="Item 1", color="blue", price=10)
        item_red = db.insert(Item, name="Item 2", color="red", price=20)

        assert _ids(db.list(Item, color__lt="m")) == {item_blue.id}
        assert item_red.id not in _ids(db.list(Item, color__lt="m"))

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        item1 = db.insert(Item, name="Item 1", color="red", created_at=moment)
        item2 = db.insert(Item, name="Item 2", color="blue", created_at=other)

        assert _ids(db.list(Item, created_at__lt=other)) == {item1.id}
        assert item2.id not in _ids(db.list(Item, created_at__lt=other))
