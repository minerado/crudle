"""Count association filters — Memory adapter.

Twin of SQLAlchemy ``count/test_count_assoc.py``.
"""

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


class TestCountAssoc:
    def test_has_many(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        blue = db.insert(Item, name="blue", color="blue", price=20)
        db.insert(ItemList, name="L1", items=[red, blue])
        db.insert(ItemList, name="L2", items=[blue])

        assert db.count(ItemList, **{"items.color": "red"}) == 1

    def test_belongs_to(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Shirt", color="blue", item_type=clothing)
        db.insert(Item, name="Orphan", color="green")

        assert db.count(Item, **{"item_type.name": "Electronics"}) == 1

    def test_many_to_many(self, db):
        gadget = db.insert(Item, name="Gadget", color="red", price=10)
        cloth = db.insert(Item, name="Cloth", color="blue", price=20)
        db.insert(Tag, name="sale", items=[gadget])
        db.insert(Tag, name="new", items=[cloth])

        assert db.count(Item, **{"tags.name": "sale"}) == 1

    def test_deep_path(self, db):
        item1 = db.insert(Item, name="i1", color="red")
        item2 = db.insert(Item, name="i2", color="blue")
        db.insert(ItemList, name="L1", items=[item1])
        db.insert(ItemList, name="L2", items=[item2])
        db.insert(Tag, name="expensive", items=[item1])
        db.insert(Tag, name="cheap", items=[item2])

        assert db.count(ItemList, **{"items.tags.name": "expensive"}) == 1

    def test_same_row_and(self, db):
        red_cheap = db.insert(Item, name="rc", color="red", price=5)
        blue_expensive = db.insert(Item, name="be", color="blue", price=50)
        db.insert(ItemList, name="Split", items=[red_cheap, blue_expensive])
        red_expensive = db.insert(Item, name="re", color="red", price=50)
        db.insert(ItemList, name="Together", items=[red_expensive])

        assert (
            db.count(ItemList, **{"items.color": "red", "items.price__gt": 15}) == 1
        )

    def test_join_fanout_counts_parents_once(self, db):
        a = db.insert(Item, name="a", color="red", price=1)
        b = db.insert(Item, name="b", color="red", price=2)
        db.insert(ItemList, name="Fan", items=[a, b])

        assert db.count(ItemList, **{"items.color": "red"}) == 1

    def test_empty_collection_excluded(self, db):
        db.insert(ItemList, name="Empty", items=[])
        red = db.insert(Item, name="red", color="red", price=10)
        db.insert(ItemList, name="Full", items=[red])

        assert db.count(ItemList, **{"items.color": "red"}) == 1

    def test_assoc_and_root_filter(self, db):
        keep_item = db.insert(Item, name="keep-child", color="red", price=10)
        drop_item = db.insert(Item, name="drop-child", color="red", price=10)
        db.insert(ItemList, name="Keep", items=[keep_item])
        db.insert(ItemList, name="Drop", items=[drop_item])

        assert db.count(ItemList, name="Keep", **{"items.color": "red"}) == 1
