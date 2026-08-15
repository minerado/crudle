"""Get_by filter operators — Memory adapter.

Twin of SQLAlchemy ``get/test_get_by_ops.py``.
"""

from datetime import datetime, timezone

import pytest

from tests.crudle.adapters.memory.models import Item


class TestGetByOps:
    def test_eq(self, db):
        keep = db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)

        assert db.get_by(Item, color="red").id == keep.id

    def test_multiple_anded(self, db):
        keep = db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=20)
        db.insert(Item, name="c", color="blue", price=10)

        assert db.get_by(Item, color="red", price=10).id == keep.id

    def test_gt(self, db):
        db.insert(Item, name="a", color="red", price=10)
        keep = db.insert(Item, name="b", color="blue", price=20)

        assert db.get_by(Item, price__gt=15).id == keep.id

    def test_ge_lt(self, db):
        db.insert(Item, name="a", color="red", price=10)
        keep = db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="green", price=30)

        assert db.get_by(Item, price__ge=15, price__lt=25).id == keep.id

    def test_in(self, db):
        keep = db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="green", price=30)

        assert db.get_by(Item, color__in=["red"]).id == keep.id

    def test_ni(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        keep = db.insert(Item, name="c", color="green", price=30)

        assert db.get_by(Item, color__ni=["red", "blue"]).id == keep.id

    def test_none_eq(self, db):
        db.insert(Item, name="a", color="red", price=10)
        keep = db.insert(Item, name="b", color=None, price=20)

        assert db.get_by(Item, color=None).id == keep.id

    def test_none_ne(self, db):
        keep = db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=None)

        assert db.get_by(Item, color="red", price__ne=None).id == keep.id

    def test_datetime(self, db):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db.insert(Item, name="old", color="red", created_at=past)
        keep = db.insert(Item, name="new", color="blue")

        assert db.get_by(Item, created_at__gt=past).id == keep.id

    def test_invalid_operator_raises(self, db):
        db.insert(Item, name="a", color="red")

        with pytest.raises(Exception, match="Forbidden operator"):
            db.get_by(Item, color__invalid_op="red")
