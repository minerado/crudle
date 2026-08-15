"""on_update_assocs=raise — Memory adapter.

Twin of SQLAlchemy ``update/test_update_on_raise.py`` (collection-focused;
Memory strategies mainly apply to collections).
"""

import pytest
from sqlalchemy.exc import IntegrityError

from tests.crudle.adapters.memory.models import Item, ItemList, Tag


class TestUpdateOnRaise:
    def test_add_existing_and_new(self, db):
        a = db.insert(Item, name="a", color="red")
        lst = db.insert(ItemList, name="L1")

        updated = db.update(
            ItemList,
            lst.id,
            items=[{"id": a.id}, {"name": "b", "color": "blue"}],
            on_update_assocs="raise",
        )

        assert len(updated.items) == 2
        assert db.count(Item) == 2

    def test_update_in_place(self, db):
        """raise keeps existing members; nested field patches are best-effort."""
        a = db.insert(Item, name="a", color="red")
        lst = db.insert(ItemList, name="L1", items=[a])

        updated = db.update(
            ItemList,
            lst.id,
            items=[{"id": a.id, "color": "blue"}],
            on_update_assocs="raise",
        )

        assert len(updated.items) >= 1
        assert any(i.id == a.id for i in updated.items)
        assert db.count(Item) == 1

    def test_update_and_add(self, db):
        a = db.insert(Item, name="a", color="red")
        lst = db.insert(ItemList, name="L1", items=[a])

        updated = db.update(
            ItemList,
            lst.id,
            items=[
                {"id": a.id, "color": "blue"},
                {"name": "b", "color": "green"},
            ],
            on_update_assocs="raise",
        )

        assert len(updated.items) == 2
        assert db.count(Item) == 2

    def test_empty_when_already_empty(self, db):
        lst = db.insert(ItemList, name="L1")

        updated = db.update(ItemList, lst.id, items=[], on_update_assocs="raise")

        assert updated.items == []

    def test_remove_raises(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        with pytest.raises(IntegrityError):
            db.update(ItemList, lst.id, items=[a], on_update_assocs="raise")

    def test_partial_remove_raises(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        c = db.insert(Item, name="c", color="blue")
        lst = db.insert(ItemList, name="L1", items=[a, b, c])

        with pytest.raises(IntegrityError):
            db.update(
                ItemList,
                lst.id,
                items=[{"id": a.id}, {"id": b.id}],
                on_update_assocs="raise",
            )

    def test_m2m_remove_raises(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        tag = db.insert(Tag, name="t1", items=[a, b])

        with pytest.raises(IntegrityError):
            db.update(Tag, tag.id, items=[a], on_update_assocs="raise")
