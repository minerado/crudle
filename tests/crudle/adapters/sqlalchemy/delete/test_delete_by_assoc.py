"""Delete_by association filters — SQLAlchemy adapter.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.models import Item, ItemList, ItemType, Tag


class TestDeleteByAssoc:
    def test_has_many(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        blue = Item.insert(db, name="blue", color="blue", price=20)
        keep = ItemList.insert(db, name="L1", items=[red, blue])
        ItemList.insert(db, name="L2", items=[blue])

        assert ItemList.delete_by(db, **{"items.color": "red"}).id == keep.id
        assert ItemList.count(db) == 1

    def test_belongs_to(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        keep = Item.insert(db, name="Phone", color="red", item_type=electronics)
        Item.insert(db, name="Shirt", color="blue", item_type=clothing)

        assert Item.delete_by(db, **{"item_type.name": "Electronics"}).id == keep.id
        assert Item.count(db) == 1

    def test_many_to_many(self, db):
        gadget = Item.insert(db, name="Gadget", color="red", price=10)
        cloth = Item.insert(db, name="Cloth", color="blue", price=20)
        Tag.insert(db, name="sale", items=[gadget])
        Tag.insert(db, name="new", items=[cloth])

        assert Item.delete_by(db, **{"tags.name": "sale"}).id == gadget.id
        assert Item.count(db) == 1

    def test_deep_path(self, db):
        item1 = Item.insert(db, name="i1", color="red")
        item2 = Item.insert(db, name="i2", color="blue")
        keep = ItemList.insert(db, name="L1", items=[item1])
        ItemList.insert(db, name="L2", items=[item2])
        Tag.insert(db, name="expensive", items=[item1])
        Tag.insert(db, name="cheap", items=[item2])

        assert (
            ItemList.delete_by(db, **{"items.tags.name": "expensive"}).id == keep.id
        )

    def test_same_row_and(self, db):
        red_cheap = Item.insert(db, name="rc", color="red", price=5)
        blue_expensive = Item.insert(db, name="be", color="blue", price=50)
        ItemList.insert(db, name="Split", items=[red_cheap, blue_expensive])
        red_expensive = Item.insert(db, name="re", color="red", price=50)
        keep = ItemList.insert(db, name="Together", items=[red_expensive])

        assert (
            ItemList.delete_by(
                db, **{"items.color": "red", "items.price__gt": 15}
            ).id
            == keep.id
        )

    def test_join_fanout_still_one_parent(self, db):
        a = Item.insert(db, name="a", color="red", price=1)
        b = Item.insert(db, name="b", color="red", price=2)
        keep = ItemList.insert(db, name="Fan", items=[a, b])

        assert ItemList.delete_by(db, **{"items.color": "red"}).id == keep.id
        assert ItemList.count(db) == 0

    def test_multiple_parents_matching_assoc_raises(self, db):
        a = Item.insert(db, name="a", color="red", price=1)
        b = Item.insert(db, name="b", color="red", price=2)
        ItemList.insert(db, name="L1", items=[a])
        ItemList.insert(db, name="L2", items=[b])

        with pytest.raises(MultipleResultsFound):
            ItemList.delete_by(db, **{"items.color": "red"})

        assert ItemList.count(db) == 2
