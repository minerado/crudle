"""Count filter operators — SQLAlchemy adapter.

One file for the list filter dialect applied to ``count`` (eq, comparisons,
in/ni, None, datetime, multi-op AND). Text (``__q``) lives in
``test_count_q.py`` (Postgres).
"""

from datetime import datetime

from tests.models import Item


class TestCountOps:
    def test_eq(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="red", price=30)

        assert Item.count(db, color="red") == 2

    def test_multiple_anded(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)
        Item.insert(db, name="c", color="blue", price=10)

        assert Item.count(db, color="red", price=10) == 1

    def test_gt(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="green", price=30)

        assert Item.count(db, price__gt=15) == 2

    def test_ge_lt(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="red", price=30)
        Item.insert(db, name="d", color="green", price=15)
        Item.insert(db, name="e", color="red", price=25)

        assert Item.count(db, color__in=["red", "blue"], price__ge=15, price__lt=30) == 2

    def test_in(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="green", price=30)

        assert Item.count(db, color__in=["red", "blue"]) == 2

    def test_ni(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="green", price=30)

        assert Item.count(db, color__ni=["red", "blue"]) == 1

    def test_none_eq(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color=None, price=20)
        Item.insert(db, name="c", color="green", price=None)

        assert Item.count(db, color=None) == 1
        assert Item.count(db, price=None) == 1

    def test_none_ne(self, db):
        """``price__ne=None`` → IS NOT NULL (replaces old count field=)."""
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=10)
        Item.insert(db, name="c", color="green", price=None)
        Item.insert(db, name="d", color="yellow", price=20)

        assert Item.count(db, price__ne=None) == 3
        assert Item.count(db, color="red", price__ne=None) == 1

    def test_datetime(self, db):
        past = datetime(2020, 1, 1)
        Item.insert(db, name="old", color="red", created_at=past)
        Item.insert(db, name="new", color="blue")

        assert Item.count(db, created_at__gt=past) == 1
