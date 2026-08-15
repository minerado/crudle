"""Update_by text-search (`q`) — Memory adapter.

Twin of SQLAlchemy ``update/test_update_by_q.py`` (Memory substring / case-insensitive).
"""

from tests.crudle.adapters.memory.models import Item


class TestUpdateByQ:
    def test_field_q(self, db):
        keep = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Samsung Galaxy", color="blue", price=20)

        assert db.update_by(Item, {"name__q": "Apple"}, name="hit").id == keep.id
        assert db.get(Item, keep.id).name == "hit"

    def test_case_insensitive(self, db):
        keep = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Samsung Galaxy", color="blue", price=20)

        assert db.update_by(Item, {"name__q": "apple"}, name="hit").id == keep.id

    def test_anded_with_filter(self, db):
        keep = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Apple MacBook", color="blue", price=20)

        assert (
            db.update_by(
                Item, {"name__q": "Apple", "color": "red"}, name="hit"
            ).id
            == keep.id
        )

    def test_miss(self, db):
        db.insert(Item, name="Apple iPhone", color="red", price=10)

        assert db.update_by(Item, {"name__q": "Nokia"}, name="x") is None
