"""Upsert_by overview — SQLAlchemy adapter.

``upsert_by(db, filters, **attrs)`` = ``update_by`` or ``insert`` on miss.
Filter dialect smoke: ``test_upsert_by_ops``; nested / assoc:
``test_upsert_by_nested``; insert-path attr rules: ``test_upsert_by_insert``.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from tests.models import Item, ItemList, Tag


class TestUpsertByBasics:
    def test_hit_updates_same_row(self, db):
        item = Item.insert(db, name="a", color="red", price=10)

        result = Item.upsert_by(db, {"color": "red"}, name="updated", price=20)

        assert result.id == item.id
        assert result.name == "updated"
        assert result.price == 20
        assert Item.count(db) == 1

    def test_miss_inserts(self, db):
        Item.insert(db, name="a", color="red")

        result = Item.upsert_by(
            db, {"name": "b"}, name="b", color="blue", price=30
        )

        assert result.name == "b"
        assert result.color == "blue"
        assert Item.count(db) == 2

    def test_multiple_raises_and_changes_nothing(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            Item.upsert_by(db, {"color": "red"}, name="x")

        assert Item.get_by(db, name="a").name == "a"
        assert Item.get_by(db, name="b").name == "b"
        assert Item.count(db) == 2

    def test_empty_filters_with_multiple_rows_raises(self, db):
        Item.insert(db, name="a", color="red")
        Item.insert(db, name="b", color="blue")

        with pytest.raises(MultipleResultsFound):
            Item.upsert_by(db, {}, name="x")

    def test_empty_filters_single_row_updates(self, db):
        item = Item.insert(db, name="only", color="red")

        assert Item.upsert_by(db, {}, name="solo").id == item.id
        assert Item.get(db, item.id).name == "solo"
        assert Item.count(db) == 1

    def test_should_raise_blocks_insert_on_miss(self, db):
        """``should_raise`` is forwarded to ``update_by`` — miss raises, no insert."""
        Item.insert(db, name="a", color="red")

        with pytest.raises(NoResultFound):
            Item.upsert_by(
                db, {"color": "blue"}, name="New", should_raise=True
            )

        assert Item.count(db) == 1

    def test_different_models(self, db):
        Item.insert(db, name="a", color="red")
        ItemList.insert(db, name="Keep")
        Tag.insert(db, name="t1")

        assert ItemList.upsert_by(db, {"name": "Keep"}, name="Kept").name == "Kept"
        assert Tag.upsert_by(db, {"name": "t1"}, name="t2").name == "t2"
        assert (
            ItemList.upsert_by(db, {"name": "New"}, name="New").name == "New"
        )
        assert ItemList.count(db) == 2

    def test_filter_nested_spelling(self, db):
        item = Item.insert(db, name="a", color="orange", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        result = Item.upsert_by(db, {"filter": {"color": "orange"}}, name="o")

        assert result.id == item.id
        assert Item.get(db, item.id).name == "o"

    def test_commit_false_on_update_not_persisted(self, db):
        item = Item.insert(db, name="a", color="red")

        result = Item.upsert_by(
            db, {"color": "red"}, name="u", commit=False
        )

        assert result.name == "u"
        db.refresh(item)
        assert item.name == "a"
