"""Upsert_by filter operators — SQLAlchemy adapter.

Smoke of the list / get_by filter dialect on upsert hit and miss paths.
"""

from datetime import datetime

from tests.models import Item


class TestUpsertByOps:
    def test_eq_hit(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        assert Item.upsert_by(db, {"color": "red"}, name="hit").id == keep.id
        assert Item.get(db, keep.id).name == "hit"
        assert Item.count(db) == 2

    def test_eq_miss_inserts(self, db):
        Item.insert(db, name="a", color="blue")

        result = Item.upsert_by(db, {"color": "red"}, name="new")

        assert result.color == "red"
        assert result.name == "new"
        assert Item.count(db) == 2

    def test_multiple_anded(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)

        assert (
            Item.upsert_by(
                db, {"color": "red", "price": 10}, name="hit"
            ).id
            == keep.id
        )

    def test_gt_hit(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color="blue", price=20)

        assert Item.upsert_by(db, {"price__gt": 15}, name="hit").id == keep.id

    def test_in_hit(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        assert (
            Item.upsert_by(db, {"color__in": ["red"]}, name="hit").id == keep.id
        )

    def test_none_eq(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color=None, price=20)

        assert Item.upsert_by(db, {"color": None}, name="hit").id == keep.id

    def test_datetime(self, db):
        past = datetime(2020, 1, 1)
        Item.insert(db, name="old", color="red", created_at=past)
        keep = Item.insert(db, name="new", color="blue")

        assert (
            Item.upsert_by(db, {"created_at__gt": past}, name="hit").id
            == keep.id
        )

    def test_ignored_list_opts_do_not_hide_match(self, db):
        keep = Item.insert(db, name="a", color="red")
        Item.insert(db, name="b", color="blue")

        result = Item.upsert_by(
            db,
            {"color": "red", "limit": 0, "skip": 99, "sort": ["-id"]},
            name="hit",
        )

        assert result.id == keep.id
        assert Item.count(db) == 2
