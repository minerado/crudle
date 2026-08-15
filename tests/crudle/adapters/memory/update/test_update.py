"""Instance update — Memory adapter.

Twin of SQLAlchemy ``update/test_update.py``. Strategies in
``test_update_on_*.py``; ``update_by`` filter dialect in ``test_update_by*``.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag
from src.crudle.adapters.memory.adapter import NotLoaded


class TestUpdate:
    def test_hit(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        updated = db.update(Item, item.id, color="blue", price=20)

        assert updated is not None
        assert updated.id == item.id
        assert updated.color == "blue"
        assert updated.price == 20
        assert db.get(Item, item.id).color == "blue"

    def test_miss(self, db):
        assert db.update(Item, 999, color="blue") is None

    def test_preserves_untouched_fields(self, db):
        item = db.insert(Item, name="a", color="red", price=10)

        db.update(Item, item.id, color="blue")

        got = db.get(Item, item.id)
        assert got.name == "a"
        assert got.price == 10

    def test_id_ignored(self, db):
        item = db.insert(Item, name="a", color="red")

        updated = db.update(Item, item.id, id=999, color="blue")

        assert updated.id == item.id
        assert db.get(Item, item.id).color == "blue"
        assert db.get(Item, 999) is None

    def test_empty_kwargs(self, db):
        item = db.insert(Item, name="a", color="red")

        updated = db.update(Item, item.id)

        assert updated.id == item.id
        assert updated.color == "red"

    def test_validation_error(self, db):
        item = db.insert(Item, name="a", color="red")

        with pytest.raises(ValueError, match="Validation error"):
            db.update(Item, item.id, name="x" * 200)

    def test_default_on_update_assocs_is_raise(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="blue")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        with pytest.raises(IntegrityError):
            db.update(ItemList, lst.id, items=[a])

    def test_untouched_relationships_not_loaded(self, db):
        item_type = db.insert(ItemType, name="Electronics")
        item = db.insert(Item, name="Phone", color="red", item_type=item_type)

        updated = db.update(Item, item.id, color="blue")

        assert updated.color == "blue"
        assert isinstance(updated.item_type, NotLoaded)

    def test_belongs_to_set(self, db):
        item = db.insert(Item, name="Phone", color="red")
        item_type = db.insert(ItemType, name="Electronics")

        updated = db.update(
            Item, item.id, item_type={"id": item_type.id, "name": "Electronics"}
        )

        assert updated.item_type_id == item_type.id
        assert db.get(Item, item.id, preload=["item_type"]).item_type.name == (
            "Electronics"
        )

    def test_m2m_set(self, db):
        item = db.insert(Item, name="Phone", color="red")
        tag = db.insert(Tag, name="sale")

        updated = db.update(Item, item.id, tags=[{"id": tag.id}])

        assert len(updated.tags) == 1
        assert updated.tags[0].id == tag.id
