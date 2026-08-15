"""Update_by overview — Memory adapter.

Twin of SQLAlchemy ``update/test_update_by.py``.
``update_by(Model, filters_dict, **attrs)`` = ``get_by`` then update.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.crudle.adapters.memory.models import Item, ItemList, Tag


class TestUpdateByBasics:
    def test_hit(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        result = db.update_by(Item, {"color": "red"}, name="updated")

        assert result.id == item.id
        assert result.name == "updated"
        assert db.get(Item, item.id).name == "updated"

    def test_miss(self, db):
        db.insert(Item, name="a", color="blue")

        assert db.update_by(Item, {"color": "red"}, name="x") is None
        assert db.get_by(Item, color="blue").name == "a"

    def test_should_raise_on_miss(self, db):
        with pytest.raises(ValueError, match="No Item found"):
            db.update_by(Item, {"color": "red"}, should_raise=True, name="x")

    def test_multiple_raises_and_updates_nothing(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            db.update_by(Item, {"color": "red"}, name="x")

        assert db.get_by(Item, name="a").name == "a"
        assert db.get_by(Item, name="b").name == "b"

    def test_empty_filters_with_multiple_rows_raises(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(Item, name="b", color="blue")

        with pytest.raises(MultipleResultsFound):
            db.update_by(Item, {}, name="x")

    def test_empty_filters_single_row(self, db):
        item = db.insert(Item, name="only", color="red")

        assert db.update_by(Item, {}, name="solo").id == item.id
        assert db.get(Item, item.id).name == "solo"

    def test_different_models(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(ItemList, name="Keep")
        db.insert(ItemList, name="Other")
        db.insert(Tag, name="t1")

        assert db.update_by(ItemList, {"name": "Keep"}, name="Kept").name == "Kept"
        assert db.update_by(Tag, {"name": "t1"}, name="t2").name == "t2"
        assert db.count(ItemList) == 2
        assert db.get_by(Tag, name="t2") is not None

    def test_filter_nested_spelling(self, db):
        item = db.insert(Item, name="a", color="orange", price=10)
        db.insert(Item, name="b", color="blue", price=20)

        result = db.update_by(Item, {"filter": {"color": "orange"}}, name="o")

        assert result.id == item.id
        assert db.get(Item, item.id).name == "o"

    def test_forwards_on_update_assocs(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="green")
        db.insert(ItemList, name="L1", items=[a, b])

        updated = db.update_by(
            ItemList,
            {"name": "L1"},
            items=[{"id": a.id}],
            on_update_assocs="nilify_all",
        )

        assert len(updated.items) == 1
        assert db.count(Item) == 2
        assert db.get(Item, b.id).item_list_id is None

    def test_specific_fields_only(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        db.update_by(Item, {"name": "a"}, color="blue")

        got = db.get(Item, item.id)
        assert got.color == "blue"
        assert got.price == 10
        assert got.name == "a"


class TestUpdateByIgnoresListOptions:
    def test_limit_cannot_silence_multiple(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            db.update_by(Item, {"color": "red", "limit": 1}, name="x")

        assert db.get_by(Item, name="a").name == "a"

    def test_skip_cannot_drop_only_match(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        result = db.update_by(Item, {"color": "red", "skip": 1}, name="kept")

        assert result.id == item.id
        assert db.get(Item, item.id).name == "kept"
