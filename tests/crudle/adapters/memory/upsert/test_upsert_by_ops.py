"""Upsert_by filter operators — Memory adapter.

Twin of SQLAlchemy ``upsert/test_upsert_by_ops.py``.
"""

from datetime import datetime, timezone

from tests.crudle.adapters.memory.models import Item


class TestUpsertByOps:
    def test_eq_hit(self, db):
        keep = db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)

        assert db.upsert_by(Item, {"color": "red"}, name="hit").id == keep.id
        assert db.get(Item, keep.id).name == "hit"
        assert db.count(Item) == 2

    def test_eq_miss_inserts(self, db):
        db.insert(Item, name="a", color="blue")

        result = db.upsert_by(Item, {"color": "red"}, name="new")

        assert result.color == "red"
        assert result.name == "new"
        assert db.count(Item) == 2

    def test_multiple_anded(self, db):
        keep = db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=20)

        assert (
            db.upsert_by(
                Item, {"color": "red", "price": 10}, name="hit"
            ).id
            == keep.id
        )

    def test_gt_hit(self, db):
        db.insert(Item, name="a", color="red", price=10)
        keep = db.insert(Item, name="b", color="blue", price=20)

        assert db.upsert_by(Item, {"price__gt": 15}, name="hit").id == keep.id

    def test_in_hit(self, db):
        keep = db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)

        assert (
            db.upsert_by(Item, {"color__in": ["red"]}, name="hit").id == keep.id
        )

    def test_none_eq(self, db):
        db.insert(Item, name="a", color="red", price=10)
        keep = db.insert(Item, name="b", color=None, price=20)

        assert db.upsert_by(Item, {"color": None}, name="hit").id == keep.id

    def test_datetime(self, db):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db.insert(Item, name="old", color="red", created_at=past)
        keep = db.insert(Item, name="new", color="blue")

        assert (
            db.upsert_by(Item, {"created_at__gt": past}, name="hit").id
            == keep.id
        )

    def test_ignored_list_opts_do_not_hide_match(self, db):
        keep = db.insert(Item, name="a", color="red")
        db.insert(Item, name="b", color="blue")

        result = db.upsert_by(
            Item,
            {"color": "red", "limit": 0, "skip": 99, "sort": ["-id"]},
            name="hit",
        )

        assert result.id == keep.id
        assert db.count(Item) == 2
