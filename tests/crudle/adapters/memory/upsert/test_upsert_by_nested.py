"""Upsert_by nested associations — Memory adapter.

Twin of SQLAlchemy ``upsert/test_upsert_by_nested.py``.
"""

import pytest

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


class TestUpsertByNestedUpdate:
    def test_forwards_on_update_assocs_nilify_all(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        result = db.upsert_by(
            ItemList,
            {"name": "L1"},
            items=[{"name": "only", "color": "blue"}],
            on_update_assocs="nilify_all",
        )

        assert result.id == lst.id
        assert len(result.items) == 1
        assert result.items[0].name == "only"
        assert db.get(Item, a.id).item_list_id is None
        assert db.get(Item, b.id).item_list_id is None

    def test_m2m_on_update(self, db):
        t1 = db.insert(Tag, name="t1")
        t2 = db.insert(Tag, name="t2")
        item = db.insert(Item, name="i", color="red", tags=[t1])

        result = db.upsert_by(
            Item,
            {"color": "red"},
            tags=[t1, t2],
            on_update_assocs="nilify_all",
        )

        assert result.id == item.id
        assert {t.name for t in result.tags} == {"t1", "t2"}


class TestUpsertByNestedInsert:
    def test_belongs_to_new_dict(self, db):
        result = db.upsert_by(
            Item,
            {"color": "red"},
            color="red",
            item_list={"name": "L1"},
        )

        assert result.item_list.name == "L1"
        assert db.count(ItemList) == 1

    def test_belongs_to_existing_by_id(self, db):
        lst = db.insert(ItemList, name="L1")

        result = db.upsert_by(
            Item,
            {"color": "red"},
            color="red",
            item_list={"id": lst.id},
        )

        assert result.item_list_id == lst.id
        assert db.count(ItemList) == 1

    def test_missing_id_raises(self, db):
        with pytest.raises(ValueError):
            db.upsert_by(
                Item,
                {"color": "red"},
                color="red",
                item_list={"id": 999},
            )

        assert db.count(Item) == 0

    def test_has_many_create(self, db):
        result = db.upsert_by(
            ItemList,
            {"name": "L1"},
            name="L1",
            items=[{"name": "a", "color": "red"}, {"name": "b", "color": "blue"}],
        )

        assert len(result.items) == 2
        assert db.count(Item) == 2

    def test_m2m_create(self, db):
        result = db.upsert_by(
            Item,
            {"color": "red"},
            name="i",
            color="red",
            tags=[{"name": "t1"}, {"name": "t2"}],
        )

        assert {t.name for t in result.tags} == {"t1", "t2"}
        assert db.count(Tag) == 2

    def test_item_type_instance(self, db):
        item_type = db.insert(ItemType, name="type_a")

        result = db.upsert_by(
            Item,
            {"name": "New"},
            name="New",
            color="blue",
            item_type=item_type,
        )

        assert result.item_type.id == item_type.id
