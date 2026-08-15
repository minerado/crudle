"""Get by primary key — Memory adapter.

Twin of SQLAlchemy ``get/test_get.py``. Preload coverage lives in
``test_preload.py``.
"""

from tests.crudle.adapters.memory.models import Item, ItemList, Tag


class TestGet:
    def test_hit(self, db):
        created = db.insert(Item, name="Test Item", color="red")

        item = db.get(Item, created.id)

        assert item is not None
        assert item.id == created.id
        assert item.name == "Test Item"

    def test_miss(self, db):
        assert db.get(Item, 1) is None
        assert db.get(Item, 999_999) is None

    def test_different_models(self, db):
        item = db.insert(Item, name="a", color="red")
        lst = db.insert(ItemList, name="L1")
        tag = db.insert(Tag, name="t1")

        assert db.get(Item, item.id).name == "a"
        assert db.get(ItemList, lst.id).name == "L1"
        assert db.get(Tag, tag.id).name == "t1"

    def test_returns_immutable_copy(self, db):
        created = db.insert(Item, name="orig", color="red")

        fetched = db.get(Item, created.id)
        fetched.name = "mutated"

        assert db.get(Item, created.id).name == "orig"
