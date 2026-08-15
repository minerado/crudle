"""Delete_by filter operators — SQLAlchemy adapter.

Smoke of the list filter dialect on ``delete_by``.
"""

from datetime import datetime

from tests.models import Item


class TestDeleteByOps:
    def test_eq(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        assert Item.delete_by(db, color="red").id == keep.id
        assert Item.count(db) == 1

    def test_multiple_anded(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)
        Item.insert(db, name="c", color="blue", price=10)

        assert Item.delete_by(db, color="red", price=10).id == keep.id
        assert Item.count(db) == 2

    def test_gt(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color="blue", price=20)

        assert Item.delete_by(db, price__gt=15).id == keep.id

    def test_in(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="green", price=30)

        assert Item.delete_by(db, color__in=["red"]).id == keep.id

    def test_none_eq(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color=None, price=20)

        assert Item.delete_by(db, color=None).id == keep.id

    def test_none_ne(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=None)

        assert Item.delete_by(db, color="red", price__ne=None).id == keep.id

    def test_datetime(self, db):
        past = datetime(2020, 1, 1)
        Item.insert(db, name="old", color="red", created_at=past)
        keep = Item.insert(db, name="new", color="blue")

        assert Item.delete_by(db, created_at__gt=past).id == keep.id
        assert Item.count(db) == 1
