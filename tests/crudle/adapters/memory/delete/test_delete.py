"""Delete by primary key — Memory adapter.

Twin concern to SQLAlchemy ``delete/test_delete.py`` (Memory API is
``db.delete(Model, id)``, not instance method).
"""

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


class TestDelete:
    def test_hit(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        deleted = db.delete(Item, item.id)

        assert deleted is not None
        assert deleted.id == item.id
        assert db.get(Item, item.id) is None

    def test_miss(self, db):
        assert db.delete(Item, 999) is None

    def test_string_id(self, db):
        item = db.insert(Item, name="a", color="red")

        deleted = db.delete(Item, str(item.id))

        assert deleted is not None
        assert db.get(Item, item.id) is None

    def test_does_not_cascade_belongs_to(self, db):
        item_type = db.insert(ItemType, name="Electronics")
        item = db.insert(Item, name="Phone", color="red", item_type=item_type)

        db.delete(Item, item.id)

        assert db.get(ItemType, item_type.id) is not None

    def test_does_not_cascade_has_many_children(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="blue")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        db.delete(ItemList, lst.id)

        assert db.get(ItemList, lst.id) is None
        assert db.get(Item, a.id) is not None
        assert db.get(Item, b.id) is not None

    def test_different_models(self, db):
        item = db.insert(Item, name="a", color="red")
        lst = db.insert(ItemList, name="L1")
        tag = db.insert(Tag, name="t1")

        db.delete(Item, item.id)
        db.delete(ItemList, lst.id)
        db.delete(Tag, tag.id)

        assert db.count(Item) == 0
        assert db.count(ItemList) == 0
        assert db.count(Tag) == 0
