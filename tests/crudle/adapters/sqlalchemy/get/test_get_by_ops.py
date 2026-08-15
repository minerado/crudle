"""Get_by filter operators — SQLAlchemy adapter.

Smoke of the list filter dialect on ``get_by`` (eq, comparisons, in/ni,
None, datetime, multi-op AND).
"""

from datetime import datetime

from tests.models import Item


class TestGetByOps:
    def test_eq(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        assert Item.get_by(db, color="red").id == keep.id

    def test_multiple_anded(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)
        Item.insert(db, name="c", color="blue", price=10)

        assert Item.get_by(db, color="red", price=10).id == keep.id

    def test_gt(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color="blue", price=20)

        assert Item.get_by(db, price__gt=15).id == keep.id

    def test_ge_lt(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="green", price=30)

        assert Item.get_by(db, price__ge=15, price__lt=25).id == keep.id

    def test_in(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="green", price=30)

        assert Item.get_by(db, color__in=["red"]).id == keep.id

    def test_ni(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        keep = Item.insert(db, name="c", color="green", price=30)

        assert Item.get_by(db, color__ni=["red", "blue"]).id == keep.id

    def test_none_eq(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color=None, price=20)

        assert Item.get_by(db, color=None).id == keep.id

    def test_none_ne(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=None)

        assert Item.get_by(db, color="red", price__ne=None).id == keep.id

    def test_datetime(self, db):
        past = datetime(2020, 1, 1)
        Item.insert(db, name="old", color="red", created_at=past)
        keep = Item.insert(db, name="new", color="blue")

        assert Item.get_by(db, created_at__gt=past).id == keep.id
