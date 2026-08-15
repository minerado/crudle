"""Get_by association filters — Memory adapter.

Twin of SQLAlchemy ``get/test_get_by_assoc.py``.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


class TestGetByAssoc:
    def test_has_many(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        blue = db.insert(Item, name="blue", color="blue", price=20)
        keep = db.insert(ItemList, name="L1", items=[red, blue])
        db.insert(ItemList, name="L2", items=[blue])

        assert db.get_by(ItemList, **{"items.color": "red"}).id == keep.id

    def test_belongs_to(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        keep = db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Shirt", color="blue", item_type=clothing)
        db.insert(Item, name="Orphan", color="green")

        assert db.get_by(Item, **{"item_type.name": "Electronics"}).id == keep.id

    def test_many_to_many(self, db):
        gadget = db.insert(Item, name="Gadget", color="red", price=10)
        cloth = db.insert(Item, name="Cloth", color="blue", price=20)
        db.insert(Tag, name="sale", items=[gadget])
        db.insert(Tag, name="new", items=[cloth])

        assert db.get_by(Item, **{"tags.name": "sale"}).id == gadget.id

    def test_deep_path(self, db):
        item1 = db.insert(Item, name="i1", color="red")
        item2 = db.insert(Item, name="i2", color="blue")
        keep = db.insert(ItemList, name="L1", items=[item1])
        db.insert(ItemList, name="L2", items=[item2])
        db.insert(Tag, name="expensive", items=[item1])
        db.insert(Tag, name="cheap", items=[item2])

        assert (
            db.get_by(ItemList, **{"items.tags.name": "expensive"}).id == keep.id
        )

    def test_same_row_and(self, db):
        red_cheap = db.insert(Item, name="rc", color="red", price=5)
        blue_expensive = db.insert(Item, name="be", color="blue", price=50)
        db.insert(ItemList, name="Split", items=[red_cheap, blue_expensive])
        red_expensive = db.insert(Item, name="re", color="red", price=50)
        keep = db.insert(ItemList, name="Together", items=[red_expensive])

        assert (
            db.get_by(
                ItemList, **{"items.color": "red", "items.price__gt": 15}
            ).id
            == keep.id
        )

    def test_join_fanout_still_one_parent(self, db):
        a = db.insert(Item, name="a", color="red", price=1)
        b = db.insert(Item, name="b", color="red", price=2)
        keep = db.insert(ItemList, name="Fan", items=[a, b])

        assert db.get_by(ItemList, **{"items.color": "red"}).id == keep.id

    def test_assoc_and_root_filter(self, db):
        keep_item = db.insert(Item, name="keep-child", color="red", price=10)
        drop_item = db.insert(Item, name="drop-child", color="red", price=10)
        keep = db.insert(ItemList, name="Keep", items=[keep_item])
        db.insert(ItemList, name="Drop", items=[drop_item])

        assert (
            db.get_by(ItemList, name="Keep", **{"items.color": "red"}).id == keep.id
        )

    def test_multiple_parents_matching_assoc_raises(self, db):
        a = db.insert(Item, name="a", color="red", price=1)
        b = db.insert(Item, name="b", color="red", price=2)
        db.insert(ItemList, name="L1", items=[a])
        db.insert(ItemList, name="L2", items=[b])

        with pytest.raises(MultipleResultsFound):
            db.get_by(ItemList, **{"items.color": "red"})
