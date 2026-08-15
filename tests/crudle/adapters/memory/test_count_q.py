"""Count text-search (`q`) — Memory adapter.

Twin of SQLAlchemy ``count/test_count_q.py``. Memory uses case-insensitive
substring match (not Postgres FTS).
"""

from tests.crudle.adapters.memory.models import Item


class TestCountQ:
    def test_field_q(self, db):
        db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Samsung Galaxy", color="blue", price=20)

        assert db.count(Item, name__q="Apple") == 1

    def test_case_insensitive_substring(self, db):
        db.insert(Item, name="Apple Pie", color="red", price=10)
        db.insert(Item, name="Banana", color="yellow", price=20)

        assert db.count(Item, name__q="apple") == 1

    def test_anded_with_filter(self, db):
        db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Apple MacBook", color="blue", price=20)

        assert db.count(Item, name__q="Apple", color="red") == 1

    def test_miss_is_zero(self, db):
        db.insert(Item, name="Apple iPhone", color="red", price=10)

        assert db.count(Item, name__q="Nokia") == 0
