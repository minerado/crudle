"""Count overview — Memory adapter.

Twin of SQLAlchemy ``count/test_count.py``. See also ``test_count_ops``,
``test_count_assoc``, ``test_count_distinct_on``.
"""

from tests.crudle.adapters.memory.models import Item, ItemList, Tag


class TestCountBasics:
    def test_total(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="green", price=30)

        assert db.count(Item) == 3

    def test_empty_table(self, db):
        assert db.count(Item) == 0

    def test_empty_filters_kwarg(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)

        assert db.count(Item, **{}) == 2

    def test_different_models(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(ItemList, name="L1")
        db.insert(ItemList, name="L2")
        db.insert(Tag, name="t1")

        assert db.count(Item) == 1
        assert db.count(ItemList) == 2
        assert db.count(Tag) == 1


class TestCountIgnoresListOptions:
    def test_limit_skip(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(Item, name="b", color="blue")
        db.insert(Item, name="c", color="green")

        assert db.count(Item, limit=1) == 3
        assert db.count(Item, skip=2) == 3
        assert db.count(Item, limit=1, skip=1) == 3

    def test_sort(self, db):
        db.insert(Item, name="a", color="red", price=30)
        db.insert(Item, name="b", color="blue", price=10)

        assert db.count(Item, sort=[{"field": "price", "order": "asc"}]) == 2

    def test_select_return_dict(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=20)
        db.insert(Item, name="c", color="blue", price=30)

        assert db.count(Item, select=["name"]) == 3
        assert db.count(Item, return_dict=True) == 3
