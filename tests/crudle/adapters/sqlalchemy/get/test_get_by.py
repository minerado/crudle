"""Get_by overview — SQLAlchemy adapter.

Basics, MultipleResultsFound, ignored list options. Deeper coverage:

- ``test_get_by_ops.py`` — filter operators
- ``test_get_by_q.py`` — text search (Postgres)
- ``test_get_by_assoc.py`` — relationship filters
- ``test_get_by_custom.py`` — ``Queries`` filters
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.models import Item, ItemList, Tag


class TestGetByBasics:
    def test_hit(self, db):
        created = Item.insert(db, name="a", color="red", price=10)

        item = Item.get_by(db, color="red")

        assert item is not None
        assert item.id == created.id

    def test_miss(self, db):
        Item.insert(db, name="a", color="blue")

        assert Item.get_by(db, color="red") is None

    def test_multiple_raises(self, db):
        Item.insert(db, name="a", color="red")
        Item.insert(db, name="b", color="red")

        with pytest.raises(MultipleResultsFound):
            Item.get_by(db, color="red")

    def test_empty_filters_with_multiple_rows_raises(self, db):
        Item.insert(db, name="a", color="red")
        Item.insert(db, name="b", color="blue")

        with pytest.raises(MultipleResultsFound):
            Item.get_by(db)

    def test_empty_filters_single_row(self, db):
        created = Item.insert(db, name="only", color="red")

        assert Item.get_by(db).id == created.id

    def test_different_models(self, db):
        Item.insert(db, name="a", color="red")
        ItemList.insert(db, name="Keep")
        ItemList.insert(db, name="Other")
        Tag.insert(db, name="t1")

        assert ItemList.get_by(db, name="Keep").name == "Keep"
        assert Tag.get_by(db, name="t1").name == "t1"

    def test_filter_dict_spelling(self, db):
        keep = Item.insert(db, name="a", color="orange", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        assert Item.get_by(db, filter={"color": "orange"}).id == keep.id
        assert (
            Item.get_by(db, filter={"color": "orange", "price": 10}).id == keep.id
        )


class TestGetByIgnoresListOptions:
    """Pagination must not hide duplicates or drop the only match."""

    def test_limit_cannot_silence_multiple(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)

        with pytest.raises(MultipleResultsFound):
            Item.get_by(db, color="red", limit=1)

    def test_skip_cannot_drop_only_match(self, db):
        created = Item.insert(db, name="a", color="red", price=10)

        assert Item.get_by(db, color="red", skip=1).id == created.id

    def test_sort_select_return_dict_distinct_ignored(self, db):
        created = Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        item = Item.get_by(
            db,
            color="red",
            sort=[{"field": "price", "order": "desc"}],
            select=["name"],
            return_dict=True,
            distinct_on=["color"],
        )

        assert item.id == created.id
        assert not isinstance(item, dict)
