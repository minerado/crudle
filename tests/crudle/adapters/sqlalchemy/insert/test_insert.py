"""Instance insert — SQLAlchemy adapter.

Scalars and None handling. Nested association depth lives in
``test_insert_nested.py``; ``commit=False`` in ``test_insert_commit_false.py``.
"""

from tests.models import Item, ItemList, Tag


class TestInsert:
    def test_scalar(self, db):
        item = Item.insert(db, name="a", color="red", price=10)

        assert item.id is not None
        assert item.color == "red"
        assert Item.get(db, item.id).price == 10

    def test_none_kwargs_are_skipped(self, db):
        """SA insert drops ``None`` kwargs (does not force NULL)."""
        item = Item.insert(db, name="a", color=None, price=10)

        assert item.name == "a"
        assert item.price == 10
        # color never set via kwargs — remains unset/NULL default
        assert Item.get(db, item.id).color is None

    def test_different_models(self, db):
        item = Item.insert(db, name="a", color="red")
        lst = ItemList.insert(db, name="L1")
        tag = Tag.insert(db, name="t1")

        assert Item.get(db, item.id).name == "a"
        assert ItemList.get(db, lst.id).name == "L1"
        assert Tag.get(db, tag.id).name == "t1"

    def test_empty_kwargs(self, db):
        item = Item.insert(db)

        assert item.id is not None
        assert Item.count(db) == 1
