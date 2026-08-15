"""Instance update — SQLAlchemy adapter.

Scalar smoke + default ``on_update_assocs=raise`` pointer.
Strategy depth lives in ``test_update_on_*.py``; ``commit=False`` in
``test_update_commit_false.py``.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from tests.models import Item, ItemList


class TestUpdate:
    def test_scalar(self, db):
        item = Item.insert(db, name="a", color="red", price=10)

        updated = item.update(db, color="blue", price=20)

        assert updated is item
        assert updated.color == "blue"
        assert updated.price == 20
        assert Item.get(db, item.id).color == "blue"

    def test_preserves_untouched_fields(self, db):
        item = Item.insert(db, name="a", color="red", price=10)

        item.update(db, color="blue")

        assert Item.get(db, item.id).name == "a"
        assert Item.get(db, item.id).price == 10

    def test_default_on_update_assocs_is_raise(self, db):
        a = Item.insert(db, name="a", color="red")
        b = Item.insert(db, name="b", color="blue")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        with pytest.raises(IntegrityError):
            lst.update(db, items=[{"id": a.id}])
