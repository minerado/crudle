"""Get_by overview — Memory adapter.

Twin of SQLAlchemy ``get/test_get_by.py``. See also ``test_get_by_ops``,
``test_get_by_q``, ``test_get_by_assoc``. Preload: ``test_preload.py``.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.crudle.adapters.memory.models import Item, ItemList, Tag


class TestGetByBasics:
    def test_hit(self, db):
        created = db.insert(Item, name="a", color="red", price=10)

        item = db.get_by(Item, color="red")

        assert item is not None
        assert item.id == created.id

    def test_miss(self, db):
        db.insert(Item, name="a", color="blue")

        assert db.get_by(Item, color="red") is None

    def test_multiple_raises(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(Item, name="b", color="red")

        with pytest.raises(MultipleResultsFound):
            db.get_by(Item, color="red")

    def test_empty_filters_with_multiple_rows_raises(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(Item, name="b", color="blue")

        with pytest.raises(MultipleResultsFound):
            db.get_by(Item)

    def test_empty_filters_single_row(self, db):
        created = db.insert(Item, name="only", color="red")

        assert db.get_by(Item).id == created.id

    def test_different_models(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(ItemList, name="Keep")
        db.insert(ItemList, name="Other")
        db.insert(Tag, name="t1")

        assert db.get_by(ItemList, name="Keep").name == "Keep"
        assert db.get_by(Tag, name="t1").name == "t1"

    def test_filter_dict_spelling(self, db):
        keep = db.insert(Item, name="a", color="orange", price=10)
        db.insert(Item, name="b", color="blue", price=20)

        assert db.get_by(Item, filter={"color": "orange"}).id == keep.id
        assert (
            db.get_by(Item, filter={"color": "orange", "price": 10}).id == keep.id
        )


class TestGetByIgnoresListOptions:
    def test_limit_cannot_silence_multiple(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            db.get_by(Item, color="red", limit=1)

    def test_skip_cannot_drop_only_match(self, db):
        created = db.insert(Item, name="a", color="red", price=10)

        assert db.get_by(Item, color="red", skip=1).id == created.id

    def test_sort_select_return_dict_distinct_ignored(self, db):
        created = db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)

        item = db.get_by(
            Item,
            color="red",
            sort=[{"field": "price", "order": "desc"}],
            select=["name"],
            return_dict=True,
            distinct_on=["color"],
        )

        assert item.id == created.id
        assert not isinstance(item, dict)
