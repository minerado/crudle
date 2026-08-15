"""List filters: not-equal operator (`ne`) — Memory adapter.

Stress twin of tests/crudle/sqlalchemy/test_list_ne.py.
Same scenarios and sections; call shape is db.method(Model, ...).
Assertions compare by id because Memory returns copies.

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — field__ne, nested path / nested dict
- Value shapes — None, empty string, numbers, etc.

Note: there is no bare-field form for `ne` (bare `field=value` is always `eq`).
"""

from datetime import datetime, timezone

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def _ids(rows):
    return {row.id for row in rows}


# ---------------------------------------------------------------------------
# Matches — when not-equal finds rows
# ---------------------------------------------------------------------------


class TestListNeMatches:
    def test_string(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        item3 = db.insert(Item, name="Item 3", color="green", price=30)

        items = db.list(Item, color__ne="red")

        assert _ids(items) == {item2.id, item3.id}
        assert item1.id not in _ids(items)

    def test_multiple_fields_anded(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name="Item 3", color="blue", price=10)

        items = db.list(Item, color="blue", price__ne=10)

        assert _ids(items) == {item2.id}
        assert item1.id not in _ids(items)


# ---------------------------------------------------------------------------
# Misses — when not-equal correctly returns empty
# ---------------------------------------------------------------------------


class TestListNeMisses:
    def test_all_rows_equal_value(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=20)

        assert db.list(Item, color__ne="red") == []

    def test_partial_and_does_not_match(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        assert db.list(Item, color="red", price__ne=10) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __ne and nested forms
# ---------------------------------------------------------------------------


class TestListNeSpellings:
    def test_nested_dotted_path(self, db):
        item_red = db.insert(Item, name="Item 1", color="red")
        item_blue = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item_red, item_blue])
        db.insert(ItemList, name="List 2", items=[item_red])

        lists = db.list(ItemList, **{"items.color__ne": "red"})

        assert _ids(lists) == {list1.id}

    def test_nested_dict_filter(self, db):
        item_red = db.insert(Item, name="Item 1", color="red")
        item_blue = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item_red, item_blue])
        db.insert(ItemList, name="List 2", items=[item_red])

        lists = db.list(ItemList, filter={"items": {"color__ne": "red"}})

        assert _ids(lists) == {list1.id}

    def test_nested_deep_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red")
        item2 = db.insert(Item, name="Item 2", color="blue")
        db.insert(ItemList, name="List 1", items=[item1])
        list2 = db.insert(ItemList, name="List 2", items=[item2])
        db.insert(Tag, name="expensive", items=[item1])
        db.insert(Tag, name="cheap", items=[item2])

        lists = db.list(ItemList, **{"items.tags.name__ne": "expensive"})

        assert _ids(lists) == {list2.id}

    def test_belongs_to_relationship(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        db.insert(Item, name="Phone", color="red", item_type=electronics)
        shirt = db.insert(Item, name="Shirt", color="blue", item_type=clothing)

        items = db.list(Item, **{"item_type.name__ne": "Electronics"})

        assert _ids(items) == {shirt.id}


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListNeValueShapes:
    def test_none_excludes_null_columns_for_value(self, db):
        """color__ne='red' excludes NULL (SQL three-valued logic)."""
        item_red = db.insert(Item, name="Item 1", color="red", price=10)
        item_blue = db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name="Item 3", color=None, price=30)

        items = db.list(Item, color__ne="red")

        assert _ids(items) == {item_blue.id}
        assert item_red.id not in _ids(items)

    def test_ne_none_means_is_not_null(self, db):
        """color__ne=None → IS NOT NULL (SQLAlchemy behavior)."""
        item_red = db.insert(Item, name="Item 1", color="red", price=10)
        item_blue = db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name="Item 3", color=None, price=30)

        items = db.list(Item, color__ne=None)

        assert _ids(items) == {item_red.id, item_blue.id}

    def test_empty_string(self, db):
        item_empty = db.insert(Item, name="", color="red", price=10)
        item_named = db.insert(Item, name="Item 2", color="blue", price=20)
        item_null = db.insert(Item, name=None, color="green", price=30)

        assert _ids(db.list(Item, name__ne="")) == {item_named.id}
        assert item_null.id not in _ids(db.list(Item, name__ne=""))
        assert item_empty.id not in _ids(db.list(Item, name__ne=""))

    def test_integer(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)

        assert _ids(db.list(Item, price__ne=10)) == {item2.id}
        assert item1.id not in _ids(db.list(Item, price__ne=10))

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        item1 = db.insert(Item, name="Item 1", color="red", created_at=moment)
        item2 = db.insert(Item, name="Item 2", color="blue", created_at=other)

        assert _ids(db.list(Item, created_at__ne=moment)) == {item2.id}
        assert item1.id not in _ids(db.list(Item, created_at__ne=moment))
