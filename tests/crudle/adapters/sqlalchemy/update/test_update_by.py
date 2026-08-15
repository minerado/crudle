"""Update_by overview — SQLAlchemy adapter.

``update_by(db, filters_dict, **attrs)`` = ``get_by(**filters)`` then update.
Deeper coverage: ``test_update_by_ops``, ``_q``, ``_assoc``, ``_custom``.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from tests.models import Item, ItemList, Tag


class TestUpdateByBasics:
    def test_hit(self, db):
        item = Item.insert(db, name="a", color="red", price=10)

        result = Item.update_by(db, {"color": "red"}, name="updated")

        assert result.id == item.id
        assert result.name == "updated"
        assert Item.get(db, item.id).name == "updated"

    def test_miss(self, db):
        Item.insert(db, name="a", color="blue")

        assert Item.update_by(db, {"color": "red"}, name="x") is None
        assert Item.get_by(db, color="blue").name == "a"

    def test_should_raise_on_miss(self, db):
        with pytest.raises(NoResultFound):
            Item.update_by(db, {"color": "red"}, should_raise=True, name="x")

    def test_multiple_raises_and_updates_nothing(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            Item.update_by(db, {"color": "red"}, name="x")

        assert Item.get_by(db, name="a").name == "a"
        assert Item.get_by(db, name="b").name == "b"

    def test_empty_filters_with_multiple_rows_raises(self, db):
        Item.insert(db, name="a", color="red")
        Item.insert(db, name="b", color="blue")

        with pytest.raises(MultipleResultsFound):
            Item.update_by(db, {}, name="x")

    def test_empty_filters_single_row(self, db):
        item = Item.insert(db, name="only", color="red")

        assert Item.update_by(db, {}, name="solo").id == item.id
        assert Item.get(db, item.id).name == "solo"

    def test_different_models(self, db):
        Item.insert(db, name="a", color="red")
        ItemList.insert(db, name="Keep")
        ItemList.insert(db, name="Other")
        Tag.insert(db, name="t1")

        assert ItemList.update_by(db, {"name": "Keep"}, name="Kept").name == "Kept"
        assert Tag.update_by(db, {"name": "t1"}, name="t2").name == "t2"
        assert ItemList.count(db) == 2
        assert Tag.get_by(db, name="t2") is not None

    def test_filter_nested_spelling(self, db):
        """filters dict may use get_by's ``filter={...}`` spelling."""
        item = Item.insert(db, name="a", color="orange", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        result = Item.update_by(db, {"filter": {"color": "orange"}}, name="o")

        assert result.id == item.id
        assert Item.get(db, item.id).name == "o"

    def test_forwards_on_update_assocs(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        updated = ItemList.update_by(
            db,
            {"name": "L1"},
            items=[{"id": a.id}],
            on_update_assocs="nilify_all",
        )

        assert len(updated.items) == 1
        assert Item.count(db) == 2
        assert Item.get(db, b.id).item_list_id is None

    def test_specific_fields_only(self, db):
        item = Item.insert(db, name="a", color="red", price=10)

        Item.update_by(db, {"name": "a"}, color="blue")

        got = Item.get(db, item.id)
        assert got.color == "blue"
        assert got.price == 10
        assert got.name == "a"


class TestUpdateByIgnoresListOptions:
    def test_limit_cannot_silence_multiple(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            Item.update_by(db, {"color": "red", "limit": 1}, name="x")

        assert Item.get_by(db, name="a").name == "a"

    def test_skip_cannot_drop_only_match(self, db):
        item = Item.insert(db, name="a", color="red", price=10)

        result = Item.update_by(db, {"color": "red", "skip": 1}, name="kept")

        assert result.id == item.id
        assert Item.get(db, item.id).name == "kept"
