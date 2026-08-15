"""on_update_assocs=nilify_all — Memory adapter.

Twin of SQLAlchemy ``update/test_update_on_nilify_all.py``.
"""

from tests.crudle.adapters.memory.models import Item, ItemList


class TestUpdateOnNilifyAll:
    def test_replace_keeps_orphans(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        updated = db.update(
            ItemList,
            lst.id,
            items=[{"id": a.id, "color": "blue"}],
            on_update_assocs="nilify_all",
        )

        assert len(updated.items) == 1
        assert updated.items[0].id == a.id
        remaining = db.get(Item, b.id)
        assert remaining is not None
        assert remaining.item_list_id is None

    def test_clear_collection_nilifies(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        updated = db.update(
            ItemList, lst.id, items=[], on_update_assocs="nilify_all"
        )

        assert updated.items == []
        assert db.count(Item) == 2
        assert db.get(Item, a.id).item_list_id is None
        assert db.get(Item, b.id).item_list_id is None
