"""Count filter operators — Memory adapter.

Twin of SQLAlchemy ``count/test_count_ops.py``.
"""

from datetime import datetime, timezone

import pytest

from tests.crudle.adapters.memory.models import Item


class TestCountOps:
    def test_eq(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="red", price=30)

        assert db.count(Item, color="red") == 2

    def test_multiple_anded(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=20)
        db.insert(Item, name="c", color="blue", price=10)

        assert db.count(Item, color="red", price=10) == 1

    def test_gt(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="green", price=30)

        assert db.count(Item, price__gt=15) == 2

    def test_ge_lt(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="red", price=30)
        db.insert(Item, name="d", color="green", price=15)
        db.insert(Item, name="e", color="red", price=25)

        assert (
            db.count(Item, color__in=["red", "blue"], price__ge=15, price__lt=30) == 2
        )

    def test_in(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="green", price=30)

        assert db.count(Item, color__in=["red", "blue"]) == 2

    def test_ni(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="green", price=30)

        assert db.count(Item, color__ni=["red", "blue"]) == 1

    def test_none_eq(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color=None, price=20)
        db.insert(Item, name="c", color="green", price=None)

        assert db.count(Item, color=None) == 1
        assert db.count(Item, price=None) == 1

    def test_none_ne(self, db):
        """``price__ne=None`` → IS NOT NULL (replaces old count field=)."""
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=10)
        db.insert(Item, name="c", color="green", price=None)
        db.insert(Item, name="d", color="yellow", price=20)

        assert db.count(Item, price__ne=None) == 3
        assert db.count(Item, color="red", price__ne=None) == 1

    def test_datetime(self, db):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db.insert(Item, name="old", color="red", created_at=past)
        db.insert(Item, name="new", color="blue")

        assert db.count(Item, created_at__gt=past) == 1

    def test_q_substring(self, db):
        db.insert(Item, name="Apple Pie", color="red", price=10)
        db.insert(Item, name="Banana", color="yellow", price=20)

        assert db.count(Item, name__q="apple") == 1

    def test_invalid_operator_raises(self, db):
        db.insert(Item, name="a", color="red")

        with pytest.raises(Exception, match="Forbidden operator"):
            db.count(Item, color__invalid_op="red")
