"""Upsert_by overview — Memory adapter.

Twin of SQLAlchemy ``upsert/test_upsert_by.py``.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.crudle.adapters.memory.models import Item, ItemList, Tag


class TestUpsertByBasics:
    def test_hit_updates_same_row(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        result = db.upsert_by(Item, {"color": "red"}, name="updated", price=20)

        assert result.id == item.id
        assert result.name == "updated"
        assert result.price == 20
        assert db.count(Item) == 1

    def test_miss_inserts(self, db):
        db.insert(Item, name="a", color="red")

        result = db.upsert_by(
            Item, {"name": "b"}, name="b", color="blue", price=30
        )

        assert result.name == "b"
        assert result.color == "blue"
        assert db.count(Item) == 2

    def test_multiple_raises_and_changes_nothing(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            db.upsert_by(Item, {"color": "red"}, name="x")

        assert db.get_by(Item, name="a").name == "a"
        assert db.get_by(Item, name="b").name == "b"
        assert db.count(Item) == 2

    def test_empty_filters_with_multiple_rows_raises(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(Item, name="b", color="blue")

        with pytest.raises(MultipleResultsFound):
            db.upsert_by(Item, {}, name="x")

    def test_empty_filters_single_row_updates(self, db):
        item = db.insert(Item, name="only", color="red")

        assert db.upsert_by(Item, {}, name="solo").id == item.id
        assert db.get(Item, item.id).name == "solo"
        assert db.count(Item) == 1

    def test_should_raise_blocks_insert_on_miss(self, db):
        db.insert(Item, name="a", color="red")

        with pytest.raises(ValueError, match="No Item found"):
            db.upsert_by(
                Item, {"color": "blue"}, name="New", should_raise=True
            )

        assert db.count(Item) == 1

    def test_different_models(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(ItemList, name="Keep")
        db.insert(Tag, name="t1")

        assert (
            db.upsert_by(ItemList, {"name": "Keep"}, name="Kept").name
            == "Kept"
        )
        assert db.upsert_by(Tag, {"name": "t1"}, name="t2").name == "t2"
        assert db.upsert_by(ItemList, {"name": "New"}, name="New").name == "New"
        assert db.count(ItemList) == 2

    def test_filter_nested_spelling(self, db):
        item = db.insert(Item, name="a", color="orange", price=10)
        db.insert(Item, name="b", color="blue", price=20)

        result = db.upsert_by(Item, {"filter": {"color": "orange"}}, name="o")

        assert result.id == item.id
        assert db.get(Item, item.id).name == "o"
