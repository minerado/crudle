"""on_update_assocs=delete_all — Memory adapter.

Twin of SQLAlchemy ``update/test_update_on_delete_all.py``.
"""

from tests.crudle.adapters.memory.models import Item, ItemList


class TestUpdateOnDeleteAll:
    def test_replace_deletes_omitted(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        c = db.insert(Item, name="c", color="yellow")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        updated = db.update(
            ItemList,
            lst.id,
            items=[c],
            on_update_assocs="delete_all",
        )

        assert len(updated.items) == 1
        assert updated.items[0].id == c.id
        assert db.get(Item, a.id) is None
        assert db.get(Item, b.id) is None

    def test_clear_collection_deletes_children(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        updated = db.update(
            ItemList, lst.id, items=[], on_update_assocs="delete_all"
        )

        assert updated.items == []
        assert db.count(Item) == 0

    def test_replace_keeps_updated_member(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        updated = db.update(
            ItemList,
            lst.id,
            items=[{"id": a.id, "color": "blue"}, {"name": "c", "color": "yellow"}],
            on_update_assocs="delete_all",
        )

        assert len(updated.items) == 2
        assert db.get(Item, b.id) is None
        assert db.count(Item) == 2
