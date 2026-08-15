"""Insert — Memory adapter.

Twin of SQLAlchemy ``insert/test_insert.py``. Nested depth in
``test_insert_nested.py``; Pydantic validation in ``test_insert_validation.py``.
"""

from tests.crudle.adapters.memory.models import Item, ItemList, Tag


class TestInsert:
    def test_scalar(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        assert item.id is not None
        assert item.color == "red"
        assert db.get(Item, item.id).price == 10

    def test_explicit_none_fields(self, db):
        item = db.insert(Item, name="a", color=None, price=None)

        assert item.name == "a"
        assert item.color is None
        assert item.price is None

    def test_different_models(self, db):
        item = db.insert(Item, name="a", color="red")
        lst = db.insert(ItemList, name="L1")
        tag = db.insert(Tag, name="t1")

        assert db.get(Item, item.id).name == "a"
        assert db.get(ItemList, lst.id).name == "L1"
        assert db.get(Tag, tag.id).name == "t1"

    def test_returns_immutable_copy(self, db):
        item = db.insert(Item, name="a", color="red")
        item.name = "mutated"

        assert db.get(Item, item.id).name == "a"
