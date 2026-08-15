"""Update_by filter operators — SQLAlchemy adapter.

Smoke of the list filter dialect on ``update_by``'s filters dict.
"""

from datetime import datetime

from tests.models import Item


class TestUpdateByOps:
    def test_eq(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        assert Item.update_by(db, {"color": "red"}, name="hit").id == keep.id
        assert Item.get(db, keep.id).name == "hit"

    def test_multiple_anded(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)
        Item.insert(db, name="c", color="blue", price=10)

        assert (
            Item.update_by(db, {"color": "red", "price": 10}, name="hit").id
            == keep.id
        )

    def test_gt(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color="blue", price=20)

        assert Item.update_by(db, {"price__gt": 15}, name="hit").id == keep.id

    def test_ge_lt(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="green", price=30)

        assert (
            Item.update_by(
                db, {"price__ge": 15, "price__lt": 25}, name="hit"
            ).id
            == keep.id
        )

    def test_in(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="green", price=30)

        assert (
            Item.update_by(db, {"color__in": ["red"]}, name="hit").id == keep.id
        )

    def test_ni(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        keep = Item.insert(db, name="c", color="green", price=30)

        assert (
            Item.update_by(
                db, {"color__ni": ["red", "blue"]}, name="hit"
            ).id
            == keep.id
        )

    def test_none_eq(self, db):
        Item.insert(db, name="a", color="red", price=10)
        keep = Item.insert(db, name="b", color=None, price=20)

        assert Item.update_by(db, {"color": None}, name="hit").id == keep.id

    def test_none_ne(self, db):
        keep = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=None)

        assert (
            Item.update_by(
                db, {"color": "red", "price__ne": None}, name="hit"
            ).id
            == keep.id
        )

    def test_datetime(self, db):
        past = datetime(2020, 1, 1)
        Item.insert(db, name="old", color="red", created_at=past)
        keep = Item.insert(db, name="new", color="blue")

        assert (
            Item.update_by(db, {"created_at__gt": past}, name="hit").id == keep.id
        )
