"""Get_by text-search (`q`) — Memory adapter.

Twin of SQLAlchemy ``get/test_get_by_q.py``. Memory uses case-insensitive
substring match (not Postgres FTS).
"""

from tests.crudle.adapters.memory.models import Item


class TestGetByQ:
    def test_field_q(self, db):
        keep = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Samsung Galaxy", color="blue", price=20)

        assert db.get_by(Item, name__q="Apple").id == keep.id

    def test_case_insensitive_substring(self, db):
        keep = db.insert(Item, name="Apple Pie", color="red", price=10)
        db.insert(Item, name="Banana", color="yellow", price=20)

        assert db.get_by(Item, name__q="apple").id == keep.id

    def test_anded_with_filter(self, db):
        keep = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Apple MacBook", color="blue", price=20)

        assert db.get_by(Item, name__q="Apple", color="red").id == keep.id

    def test_miss(self, db):
        db.insert(Item, name="Apple iPhone", color="red", price=10)

        assert db.get_by(Item, name__q="Nokia") is None
