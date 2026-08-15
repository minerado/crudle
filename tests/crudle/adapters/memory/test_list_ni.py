"""List filters: not-in operator (`ni`) — Memory adapter.

Stress twin of tests/crudle/adapters/sqlalchemy/list/test_list_ni.py.
Same scenarios and sections; call shape is db.method(Model, ...).
Assertions compare by id because Memory returns copies.
"""

from datetime import datetime, timezone

import pytest

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def _ids(rows):
    return {row.id for row in rows}


class TestListNiMatches:
    def test_string_list(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)
        item3 = db.insert(Item, name="Item 3", color="green", price=30)
        item4 = db.insert(Item, name="Item 4", color="yellow", price=40)

        items = db.list(Item, color__ni=["red", "blue"])

        assert _ids(items) == {item3.id, item4.id}
        assert item1.id not in _ids(items)
        assert item2.id not in _ids(items)

    def test_multiple_fields_anded(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=30)

        items = db.list(Item, color="red", price__ni=[10])

        assert _ids(items) == {item2.id}
        assert item1.id not in _ids(items)


class TestListNiMisses:
    def test_all_rows_in_list(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="blue", price=20)

        assert db.list(Item, color__ni=["red", "blue"]) == []

    def test_partial_and_does_not_match(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        assert db.list(Item, color="red", price__ni=[10]) == []


class TestListNiSpellings:
    def test_nested_dotted_path(self, db):
        item_red = db.insert(Item, name="Item 1", color="red")
        item_blue = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item_red, item_blue])
        db.insert(ItemList, name="List 2", items=[item_red])

        lists = db.list(ItemList, **{"items.color__ni": ["red"]})

        assert _ids(lists) == {list1.id}

    def test_nested_dict_filter(self, db):
        item_red = db.insert(Item, name="Item 1", color="red")
        item_blue = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item_red, item_blue])
        db.insert(ItemList, name="List 2", items=[item_red])

        lists = db.list(ItemList, filter={"items": {"color__ni": ["red"]}})

        assert _ids(lists) == {list1.id}

    def test_nested_deep_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red")
        item2 = db.insert(Item, name="Item 2", color="blue")
        db.insert(ItemList, name="List 1", items=[item1])
        list2 = db.insert(ItemList, name="List 2", items=[item2])
        db.insert(Tag, name="expensive", items=[item1])
        db.insert(Tag, name="cheap", items=[item2])

        lists = db.list(ItemList, **{"items.tags.name__ni": ["expensive"]})

        assert _ids(lists) == {list2.id}

    def test_belongs_to_relationship(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        db.insert(Item, name="Phone", color="red", item_type=electronics)
        shirt = db.insert(Item, name="Shirt", color="blue", item_type=clothing)

        items = db.list(Item, **{"item_type.name__ni": ["Electronics"]})

        assert _ids(items) == {shirt.id}


class TestListNiValueShapes:
    def test_null_column_excluded_for_nonempty_list(self, db):
        item_green = db.insert(Item, name="Item 1", color="green", price=10)
        db.insert(Item, name="Item 2", color=None, price=20)
        db.insert(Item, name="Item 3", color="red", price=30)

        items = db.list(Item, color__ni=["red", "blue"])

        assert _ids(items) == {item_green.id}

    def test_none_in_list_matches_nothing(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="blue", price=20)
        db.insert(Item, name="Item 3", color=None, price=30)

        assert db.list(Item, color__ni=["red", None]) == []

    def test_empty_list_includes_null(self, db):
        item_red = db.insert(Item, name="Item 1", color="red", price=10)
        item_null = db.insert(Item, name="Item 2", color=None, price=20)

        assert _ids(db.list(Item, color__ni=[])) == {item_red.id, item_null.id}

    def test_none_filter_value_rejected(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)

        with pytest.raises(Exception, match="None"):
            db.list(Item, color__ni=None)

    def test_empty_string(self, db):
        item_empty = db.insert(Item, name="", color="red", price=10)
        item_named = db.insert(Item, name="Item 2", color="blue", price=20)

        assert _ids(db.list(Item, name__ni=[""])) == {item_named.id}
        assert item_empty.id not in _ids(db.list(Item, name__ni=[""]))

    def test_integer(self, db):
        item1 = db.insert(Item, name="Item 1", color="red", price=10)
        item2 = db.insert(Item, name="Item 2", color="blue", price=20)

        assert _ids(db.list(Item, price__ni=[10])) == {item2.id}
        assert item1.id not in _ids(db.list(Item, price__ni=[10]))

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        item1 = db.insert(Item, name="Item 1", color="red", created_at=moment)
        item2 = db.insert(Item, name="Item 2", color="blue", created_at=other)

        assert _ids(db.list(Item, created_at__ni=[moment])) == {item2.id}
        assert item1.id not in _ids(db.list(Item, created_at__ni=[moment]))
