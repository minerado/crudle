"""Upsert_by nested associations — SQLAlchemy adapter.

Update path forwards ``on_update_assocs``; insert path reuses insert
nested create / link behavior.
"""

import pytest
from sqlalchemy.exc import NoResultFound

from tests.models import Item, ItemList, ItemType, Tag


class TestUpsertByNestedUpdate:
    def test_forwards_on_update_assocs_nilify_all(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        result = ItemList.upsert_by(
            db,
            {"name": "L1"},
            items=[{"name": "only", "color": "blue"}],
            on_update_assocs="nilify_all",
        )

        assert result.id == lst.id
        assert len(result.items) == 1
        assert result.items[0].name == "only"
        assert Item.get(db, a.id).item_list_id is None
        assert Item.get(db, b.id).item_list_id is None

    def test_m2m_on_update(self, db):
        t1 = Tag.insert(db, name="t1")
        t2 = Tag.insert(db, name="t2")
        item = Item.insert(db, color="red", tags=[t1])

        result = Item.upsert_by(
            db,
            {"color": "red"},
            tags=[t1, t2],
            on_update_assocs="nilify_all",
        )

        assert result.id == item.id
        assert {t.name for t in result.tags} == {"t1", "t2"}


class TestUpsertByNestedInsert:
    def test_belongs_to_new_dict(self, db):
        result = Item.upsert_by(
            db,
            {"color": "red"},
            color="red",
            item_list={"name": "L1"},
        )

        assert result.item_list.name == "L1"
        assert ItemList.count(db) == 1

    def test_belongs_to_existing_by_id(self, db):
        lst = ItemList.insert(db, name="L1")

        result = Item.upsert_by(
            db,
            {"color": "red"},
            color="red",
            item_list={"id": lst.id},
        )

        assert result.item_list_id == lst.id
        assert ItemList.count(db) == 1

    def test_missing_id_raises(self, db):
        with pytest.raises(NoResultFound, match="ItemList"):
            Item.upsert_by(
                db,
                {"color": "red"},
                color="red",
                item_list={"id": 999},
            )

        assert Item.count(db) == 0

    def test_has_many_create(self, db):
        result = ItemList.upsert_by(
            db,
            {"name": "L1"},
            name="L1",
            items=[{"color": "red"}, {"color": "blue"}],
        )

        assert len(result.items) == 2
        assert Item.count(db) == 2

    def test_m2m_create(self, db):
        result = Item.upsert_by(
            db,
            {"color": "red"},
            color="red",
            tags=[{"name": "t1"}, {"name": "t2"}],
        )

        assert {t.name for t in result.tags} == {"t1", "t2"}
        assert Tag.count(db) == 2

    def test_item_type_instance(self, db):
        item_type = ItemType.insert(db, name="type_a")

        result = Item.upsert_by(
            db,
            {"name": "New"},
            name="New",
            color="blue",
            item_type=item_type,
        )

        assert result.item_type.id == item_type.id
