"""Update_by association filters — Memory adapter.

Twin of SQLAlchemy ``update/test_update_by_assoc.py``.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


class TestUpdateByAssoc:
    def test_has_many(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        blue = db.insert(Item, name="blue", color="blue", price=20)
        keep = db.insert(ItemList, name="L1", items=[red, blue])
        db.insert(ItemList, name="L2", items=[blue])

        assert (
            db.update_by(ItemList, {"items.color": "red"}, name="hit").id
            == keep.id
        )
        assert db.get(ItemList, keep.id).name == "hit"

    def test_belongs_to(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        keep = db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Shirt", color="blue", item_type=clothing)

        assert (
            db.update_by(
                Item, {"item_type.name": "Electronics"}, name="hit"
            ).id
            == keep.id
        )

    def test_many_to_many(self, db):
        gadget = db.insert(Item, name="Gadget", color="red", price=10)
        cloth = db.insert(Item, name="Cloth", color="blue", price=20)
        db.insert(Tag, name="sale", items=[gadget])
        db.insert(Tag, name="new", items=[cloth])

        assert (
            db.update_by(Item, {"tags.name": "sale"}, name="hit").id == gadget.id
        )
        assert db.get(Item, gadget.id).name == "hit"

    def test_deep_path(self, db):
        item1 = db.insert(Item, name="i1", color="red")
        item2 = db.insert(Item, name="i2", color="blue")
        keep = db.insert(ItemList, name="L1", items=[item1])
        db.insert(ItemList, name="L2", items=[item2])
        db.insert(Tag, name="expensive", items=[item1])
        db.insert(Tag, name="cheap", items=[item2])

        assert (
            db.update_by(
                ItemList, {"items.tags.name": "expensive"}, name="hit"
            ).id
            == keep.id
        )

    def test_same_row_and(self, db):
        red_cheap = db.insert(Item, name="rc", color="red", price=5)
        blue_expensive = db.insert(Item, name="be", color="blue", price=50)
        db.insert(ItemList, name="Split", items=[red_cheap, blue_expensive])
        red_expensive = db.insert(Item, name="re", color="red", price=50)
        keep = db.insert(ItemList, name="Together", items=[red_expensive])

        assert (
            db.update_by(
                ItemList,
                {"items.color": "red", "items.price__gt": 15},
                name="hit",
            ).id
            == keep.id
        )

    def test_join_fanout_still_one_parent(self, db):
        a = db.insert(Item, name="a", color="red", price=1)
        b = db.insert(Item, name="b", color="red", price=2)
        keep = db.insert(ItemList, name="Fan", items=[a, b])

        assert (
            db.update_by(ItemList, {"items.color": "red"}, name="hit").id
            == keep.id
        )

    def test_multiple_parents_matching_assoc_raises(self, db):
        a = db.insert(Item, name="a", color="red", price=1)
        b = db.insert(Item, name="b", color="red", price=2)
        db.insert(ItemList, name="L1", items=[a])
        db.insert(ItemList, name="L2", items=[b])

        with pytest.raises(MultipleResultsFound):
            db.update_by(ItemList, {"items.color": "red"}, name="x")

        assert db.get_by(ItemList, name="L1").name == "L1"
        assert db.get_by(ItemList, name="L2").name == "L2"
