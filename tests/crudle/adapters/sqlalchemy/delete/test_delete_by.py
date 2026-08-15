"""Delete_by overview — SQLAlchemy adapter.

``delete_by`` = ``get_by`` then delete. Basics, MultipleResultsFound,
ignored list options. Deeper coverage:

- ``test_delete_by_ops.py`` — filter operators
- ``test_delete_by_q.py`` — text search (Postgres)
- ``test_delete_by_assoc.py`` — relationship filters
- ``test_delete_by_custom.py`` — ``Queries`` filters
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.models import Item, ItemList, Tag


class TestDeleteByBasics:
    def test_hit(self, db):
        item = Item.insert(db, name="a", color="red", price=10)

        result = Item.delete_by(db, color="red")

        assert result is item
        assert Item.get(db, item.id) is None

    def test_miss(self, db):
        Item.insert(db, name="a", color="blue")

        assert Item.delete_by(db, color="red") is None
        assert Item.count(db) == 1

    def test_multiple_raises_and_deletes_nothing(self, db):
        Item.insert(db, name="a", color="red")
        Item.insert(db, name="b", color="red")

        with pytest.raises(MultipleResultsFound):
            Item.delete_by(db, color="red")

        assert Item.count(db) == 2

    def test_empty_filters_with_multiple_rows_raises(self, db):
        Item.insert(db, name="a", color="red")
        Item.insert(db, name="b", color="blue")

        with pytest.raises(MultipleResultsFound):
            Item.delete_by(db)

        assert Item.count(db) == 2

    def test_empty_filters_single_row(self, db):
        item = Item.insert(db, name="only", color="red")

        assert Item.delete_by(db).id == item.id
        assert Item.count(db) == 0

    def test_different_models(self, db):
        Item.insert(db, name="a", color="red")
        ItemList.insert(db, name="Keep")
        ItemList.insert(db, name="Other")
        Tag.insert(db, name="t1")

        assert ItemList.delete_by(db, name="Keep").name == "Keep"
        assert Tag.delete_by(db, name="t1").name == "t1"
        assert ItemList.count(db) == 1
        assert Tag.count(db) == 0

    def test_filter_dict_spelling(self, db):
        item = Item.insert(db, name="a", color="orange", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        assert Item.delete_by(db, filter={"color": "orange"}).id == item.id
        assert Item.count(db) == 1


class TestDeleteByIgnoresListOptions:
    def test_limit_cannot_silence_multiple(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            Item.delete_by(db, color="red", limit=1)

        assert Item.count(db) == 2

    def test_skip_cannot_drop_only_match(self, db):
        item = Item.insert(db, name="a", color="red", price=10)

        assert Item.delete_by(db, color="red", skip=1).id == item.id
        assert Item.count(db) == 0
