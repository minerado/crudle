"""List filters: membership operator (`in`) — Memory adapter.

Stress twin of tests/crudle/sqlalchemy/test_list_in.py.
Same scenarios and sections; call shape is db.method(Model, ...).
Assertions compare by id because Memory returns copies.
"""

from datetime import datetime, timezone

import pytest

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def _ids(rows):
    return {row.id for row in rows}


class TestListInMatches:
    def test_string_list(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        item3 = db.insert(Item, name="Item 3", color="green", price=30)

        items = db.list(Item, color__in=["red", "blue"])

        assert _ids(items) == {item1.id, item2.id}
        assert item3.id not in _ids(items)

    def test_multiple_fields_anded(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=10)

        items = db.list(Item, color="red", price__in=[10, 30])

        assert _ids(items) == {item1.id}
        assert item2.id not in _ids(items)


class TestListInMisses:
    def test_no_overlap(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="blue", price=20)

        assert db.list(Item, color__in=["purple", "orange"]) == []

    def test_empty_list(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        assert db.list(Item, color__in=[]) == []

    def test_partial_and_does_not_match(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        assert db.list(Item, color="red", price__in=[99]) == []


class TestListInSpellings:
    def test_nested_dotted_path(self, db):
        item_red = db.insert(Item, name="Item 1", color="red")
        item_blue = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item_red, item_blue])
        db.insert(ItemList, name="List 2", items=[item_red])

        lists = db.list(ItemList, **{"items.color__in": ["blue", "green"]})

        assert _ids(lists) == {list1.id}

    def test_nested_dict_filter(self, db):
        item_red = db.insert(Item, name="Item 1", color="red")
        item_blue = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item_red, item_blue])
        db.insert(ItemList, name="List 2", items=[item_red])

        lists = db.list(ItemList, filter={"items": {"color__in": ["blue", "green"]}})

        assert _ids(lists) == {list1.id}

    def test_nested_deep_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red")
        item2 = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item1])
        db.insert(ItemList, name="List 2", items=[item2])
        db.insert(Tag, name="expensive", items=[item1])
        db.insert(Tag, name="cheap", items=[item2])

        lists = db.list(ItemList, **{"items.tags.name__in": ["expensive"]})

        assert _ids(lists) == {list1.id}

    def test_belongs_to_relationship(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        phone = db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Shirt", color="blue", item_type=clothing)

        items = db.list(Item, **{"item_type.name__in": ["Electronics"]})

        assert _ids(items) == {phone.id}


class TestListInValueShapes:
    def test_null_column_excluded(self, db):
        """NULL column is never IN (...), even with None in the list."""
        item_red = db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color=None, price=20)

        assert _ids(db.list(Item, color__in=["red", "blue"])) == {item_red.id}
        assert _ids(db.list(Item, color__in=["red", None])) == {item_red.id}

    def test_none_filter_value_rejected(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        with pytest.raises(Exception, match="None"):
            db.list(Item, color__in=None)

    def test_empty_string(self, db):
        item_empty = db.insert(Item, name="", color="red", price=10)
        item_named = db.insert(Item, name="Item 2", color="blue", price=20)

        assert _ids(db.list(Item, name__in=[""])) == {item_empty.id}
        assert item_named.id not in _ids(db.list(Item, name__in=[""]))

    def test_integer(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        item3 = db.insert(Item, name="Item 3", color="green", price=30)

        assert _ids(db.list(Item, price__in=[10, 30])) == {item1.id, item3.id}
        assert item2.id not in _ids(db.list(Item, price__in=[10, 30]))

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        item1 = db.insert(Item, name="Item 1", color="red", created_at=moment)
        item2 = db.insert(Item, name="Item 2", color="blue", created_at=other)

        assert _ids(db.list(Item, created_at__in=[moment])) == {item1.id}
        assert item2.id not in _ids(db.list(Item, created_at__in=[moment]))
