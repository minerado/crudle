"""List filters: equality operator (`eq` / bare field) — Memory adapter.

Stress twin of tests/crudle/sqlalchemy/test_list_eq.py.
Same scenarios and sections; call shape is db.method(Model, ...) instead of
Model.method(db, ...). Assertions compare by id because Memory returns copies.

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — bare field, field__eq, nested path / nested dict
- Value shapes — None, empty string, numbers, etc.
"""

from datetime import datetime, timezone

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def _ids(rows):
    return {row.id for row in rows}


# ---------------------------------------------------------------------------
# Matches — when equality finds rows
# ---------------------------------------------------------------------------


class TestListEqMatches:
    def test_bare_field_string(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        item3 = db.insert(Item, name="Item 3", color="red", price=30)

        red_items = db.list(Item, color="red")

        assert _ids(red_items) == {item1.id, item3.id}
        assert item2.id not in _ids(red_items)

    def test_multiple_fields_anded(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=10)

        items = db.list(Item, color="red", price__eq=10)

        assert _ids(items) == {item1.id}


# ---------------------------------------------------------------------------
# Misses — when equality correctly returns empty
# ---------------------------------------------------------------------------


class TestListEqMisses:
    def test_no_matching_value(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        assert db.list(Item, color="purple") == []
        assert db.list(Item, color__eq="purple") == []

    def test_partial_and_does_not_match(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        assert db.list(Item, color="red", price__eq=99) == []


# ---------------------------------------------------------------------------
# Spellings — bare vs __eq vs nested forms
# ---------------------------------------------------------------------------


class TestListEqSpellings:
    def test_explicit_eq_matches_bare(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="blue", price=20)
        item3 = db.insert(Item, name="Item 3", color="red", price=30)

        bare = db.list(Item, color="red")
        explicit = db.list(Item, color__eq="red")

        assert _ids(bare) == {item1.id, item3.id}
        assert _ids(explicit) == _ids(bare)

    def test_nested_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red")
        item2 = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item1, item2])
        db.insert(ItemList, name="List 2", items=[item2])

        lists = db.list(ItemList, **{"items.color": "red"})

        assert _ids(lists) == {list1.id}

    def test_nested_dotted_path_with_explicit_eq(self, db):
        item1 = db.insert(Item, name="Item 1", color="red")
        item2 = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item1, item2])
        db.insert(ItemList, name="List 2", items=[item2])

        lists = db.list(ItemList, **{"items.color__eq": "red"})

        assert _ids(lists) == {list1.id}

    def test_nested_dict_filter(self, db):
        item1 = db.insert(Item, name="Item 1", color="red")
        item2 = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item1, item2])
        db.insert(ItemList, name="List 2", items=[item2])

        lists = db.list(ItemList, filter={"items": {"color": "red"}})

        assert _ids(lists) == {list1.id}

    def test_nested_deep_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red")
        item2 = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item1])
        db.insert(ItemList, name="List 2", items=[item2])
        db.insert(Tag, name="expensive", items=[item1])
        db.insert(Tag, name="cheap", items=[item2])

        lists = db.list(ItemList, **{"items.tags.name": "expensive"})

        assert _ids(lists) == {list1.id}

    def test_belongs_to_relationship(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        item1 = db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Shirt", color="blue", item_type=clothing)

        items = db.list(Item, **{"item_type.name": "Electronics"})

        assert _ids(items) == {item1.id}


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListEqValueShapes:
    def test_none(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color=None, price=20)
        item3 = db.insert(Item, name="Item 3", color="blue", price=None)

        assert _ids(db.list(Item, color=None)) == {item2.id}
        assert _ids(db.list(Item, color__eq=None)) == {item2.id}
        assert _ids(db.list(Item, price=None)) == {item3.id}
        assert _ids(db.list(Item, price__eq=None)) == {item3.id}

    def test_empty_string(self, db):
        item_empty = db.insert(Item, name="", color="red", price=10)
        db.insert(Item, name="Item 2", color="blue", price=20)
        item_null = db.insert(Item, name=None, color="green", price=30)

        assert _ids(db.list(Item, name="")) == {item_empty.id}
        assert _ids(db.list(Item, name__eq="")) == {item_empty.id}
        assert _ids(db.list(Item, name=None)) == {item_null.id}
        assert _ids(db.list(Item, name__eq=None)) == {item_null.id}

    def test_integer(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="blue", price=20)

        assert _ids(db.list(Item, price=10)) == {item1.id}
        assert _ids(db.list(Item, price__eq=10)) == {item1.id}

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        item1 = db.insert(Item, name="Item 1", color="red", created_at=moment)
        db.insert(Item, name="Item 2", color="blue", created_at=other)

        assert _ids(db.list(Item, created_at=moment)) == {item1.id}
        assert _ids(db.list(Item, created_at__eq=moment)) == {item1.id}
