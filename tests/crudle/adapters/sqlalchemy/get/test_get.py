"""Get by primary key — SQLAlchemy adapter.

``get`` is ID lookup only. Filter dialect lives on ``get_by`` (see
``test_get_by*.py``).
"""

from tests.models import Item, ItemList, Tag


class TestGet:
    def test_hit(self, db):
        created = Item.insert(db, name="Test Item", color="red")

        item = Item.get(db, created.id)

        assert item is not None
        assert item.id == created.id
        assert item.name == "Test Item"

    def test_miss(self, db):
        assert Item.get(db, 1) is None
        assert Item.get(db, 999_999) is None

    def test_different_models(self, db):
        item = Item.insert(db, name="a", color="red")
        lst = ItemList.insert(db, name="L1")
        tag = Tag.insert(db, name="t1")

        assert Item.get(db, item.id).name == "a"
        assert ItemList.get(db, lst.id).name == "L1"
        assert Tag.get(db, tag.id).name == "t1"
