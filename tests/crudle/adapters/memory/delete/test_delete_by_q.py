"""Delete_by text-search (`q`) — Memory adapter.
"""

from tests.crudle.adapters.memory.models import Item


class TestDeleteByQ:
    def test_field_q(self, db):
        keep = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Samsung Galaxy", color="blue", price=20)

        assert db.delete_by(Item, name__q="Apple").id == keep.id
        assert db.count(Item) == 1

    def test_anded_with_filter(self, db):
        keep = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Apple MacBook", color="blue", price=20)

        assert db.delete_by(Item, name__q="Apple", color="red").id == keep.id

    def test_miss(self, db):
        db.insert(Item, name="Apple iPhone", color="red", price=10)

        assert db.delete_by(Item, name__q="Nokia") is None
        assert db.count(Item) == 1
