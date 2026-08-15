"""Get_by association filters — SQLAlchemy adapter.

Twin concern to ``list/test_list_assoc.py`` / ``count/test_count_assoc.py``.
"""

import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.models import Item, ItemList, ItemType, Tag


class TestGetByAssoc:
    def test_has_many(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        blue = Item.insert(db, name="blue", color="blue", price=20)
        keep = ItemList.insert(db, name="L1", items=[red, blue])
        ItemList.insert(db, name="L2", items=[blue])

        assert ItemList.get_by(db, **{"items.color": "red"}).id == keep.id

    def test_belongs_to(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        keep = Item.insert(db, name="Phone", color="red", item_type=electronics)
        Item.insert(db, name="Shirt", color="blue", item_type=clothing)
        Item.insert(db, name="Orphan", color="green")

        assert Item.get_by(db, **{"item_type.name": "Electronics"}).id == keep.id

    def test_many_to_many(self, db):
        gadget = Item.insert(db, name="Gadget", color="red", price=10)
        cloth = Item.insert(db, name="Cloth", color="blue", price=20)
        Tag.insert(db, name="sale", items=[gadget])
        Tag.insert(db, name="new", items=[cloth])

        assert Item.get_by(db, **{"tags.name": "sale"}).id == gadget.id

    def test_deep_path(self, db):
        item1 = Item.insert(db, name="i1", color="red")
        item2 = Item.insert(db, name="i2", color="blue")
        keep = ItemList.insert(db, name="L1", items=[item1])
        ItemList.insert(db, name="L2", items=[item2])
        Tag.insert(db, name="expensive", items=[item1])
        Tag.insert(db, name="cheap", items=[item2])

        assert (
            ItemList.get_by(db, **{"items.tags.name": "expensive"}).id == keep.id
        )

    def test_same_row_and(self, db):
        red_cheap = Item.insert(db, name="rc", color="red", price=5)
        blue_expensive = Item.insert(db, name="be", color="blue", price=50)
        ItemList.insert(db, name="Split", items=[red_cheap, blue_expensive])
        red_expensive = Item.insert(db, name="re", color="red", price=50)
        keep = ItemList.insert(db, name="Together", items=[red_expensive])

        assert (
            ItemList.get_by(
                db, **{"items.color": "red", "items.price__gt": 15}
            ).id
            == keep.id
        )

    def test_join_fanout_still_one_parent(self, db):
        """Two matching children must not raise MultipleResultsFound."""
        a = Item.insert(db, name="a", color="red", price=1)
        b = Item.insert(db, name="b", color="red", price=2)
        keep = ItemList.insert(db, name="Fan", items=[a, b])

        assert ItemList.get_by(db, **{"items.color": "red"}).id == keep.id

    def test_assoc_and_root_filter(self, db):
        keep_item = Item.insert(db, name="keep-child", color="red", price=10)
        drop_item = Item.insert(db, name="drop-child", color="red", price=10)
        keep = ItemList.insert(db, name="Keep", items=[keep_item])
        ItemList.insert(db, name="Drop", items=[drop_item])

        assert (
            ItemList.get_by(db, name="Keep", **{"items.color": "red"}).id == keep.id
        )

    def test_multiple_parents_matching_assoc_raises(self, db):
        a = Item.insert(db, name="a", color="red", price=1)
        b = Item.insert(db, name="b", color="red", price=2)
        ItemList.insert(db, name="L1", items=[a])
        ItemList.insert(db, name="L2", items=[b])

        with pytest.raises(MultipleResultsFound):
            ItemList.get_by(db, **{"items.color": "red"})
