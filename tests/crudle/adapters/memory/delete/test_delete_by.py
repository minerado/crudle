"""Delete_by overview — Memory adapter.

Twin of SQLAlchemy ``delete/test_delete_by.py``. See also
``test_delete_by_ops``, ``test_delete_by_q``, ``test_delete_by_assoc``.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.crudle.adapters.memory.models import Item, ItemList, Tag


class TestDeleteByBasics:
    def test_hit(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        result = db.delete_by(Item, color="red")

        assert result is not None
        assert result.id == item.id
        assert db.get(Item, item.id) is None

    def test_miss(self, db):
        db.insert(Item, name="a", color="blue")

        assert db.delete_by(Item, color="red") is None
        assert db.count(Item) == 1

    def test_multiple_raises_and_deletes_nothing(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(Item, name="b", color="red")

        with pytest.raises(MultipleResultsFound):
            db.delete_by(Item, color="red")

        assert db.count(Item) == 2

    def test_empty_filters_with_multiple_rows_raises(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(Item, name="b", color="blue")

        with pytest.raises(MultipleResultsFound):
            db.delete_by(Item)

        assert db.count(Item) == 2

    def test_empty_filters_single_row(self, db):
        item = db.insert(Item, name="only", color="red")

        assert db.delete_by(Item).id == item.id
        assert db.count(Item) == 0

    def test_different_models(self, db):
        db.insert(Item, name="a", color="red")
        db.insert(ItemList, name="Keep")
        db.insert(ItemList, name="Other")
        db.insert(Tag, name="t1")

        assert db.delete_by(ItemList, name="Keep").name == "Keep"
        assert db.delete_by(Tag, name="t1").name == "t1"
        assert db.count(ItemList) == 1
        assert db.count(Tag) == 0

    def test_filter_dict_spelling(self, db):
        item = db.insert(Item, name="a", color="orange", price=10)
        db.insert(Item, name="b", color="blue", price=20)

        assert db.delete_by(Item, filter={"color": "orange"}).id == item.id
        assert db.count(Item) == 1


class TestDeleteByIgnoresListOptions:
    def test_limit_cannot_silence_multiple(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            db.delete_by(Item, color="red", limit=1)

        assert db.count(Item) == 2

    def test_skip_cannot_drop_only_match(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        assert db.delete_by(Item, color="red", skip=1).id == item.id
        assert db.count(Item) == 0
