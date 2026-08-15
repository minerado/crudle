"""on_update_assocs=nilify_all — SQLAlchemy adapter.

Replace collection: omitted members are unlinked, not deleted.
"""

from tests.models import Item, ItemList, ItemTag, ItemType, Tag


class TestUpdateOnNilifyAll:
    def test_replace_keeps_orphans(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        updated = lst.update(
            db,
            items=[{"id": a.id, "color": "blue"}],
            on_update_assocs="nilify_all",
        )

        assert len(updated.items) == 1
        assert Item.count(db) == 2
        assert Item.get(db, b.id).item_list_id is None

    def test_clear_collection_nilifies(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        updated = lst.update(db, items=[], on_update_assocs="nilify_all")

        assert updated.items == []
        assert Item.count(db) == 2
        assert Item.get(db, a.id).item_list_id is None
        assert Item.get(db, b.id).item_list_id is None

    def test_belongs_to_none_keeps_related(self, db):
        item_type = ItemType.insert(db, name="Electronics")
        item = Item.insert(db, color="red", item_type=item_type)

        updated = item.update(db, item_type=None, on_update_assocs="nilify_all")

        assert updated.item_type is None
        assert ItemType.count(db) == 1

    def test_mixed_dict_and_instance(self, db):
        a = Item.insert(db, color="red")
        fresh = Item(color="green")
        lst = ItemList.insert(db, name="L1")

        updated = lst.update(
            db,
            items=[{"id": a.id, "color": "blue"}, fresh, {"color": "yellow"}],
            on_update_assocs="nilify_all",
        )

        assert len(updated.items) == 3
        assert Item.count(db) == 3

    def test_deep_nested_nilify_keeps_types(self, db):
        t1 = ItemType.insert(db, name="type_1")
        t2 = ItemType.insert(db, name="type_2")
        a = Item.insert(db, color="red", item_type=t1)
        b = Item.insert(db, color="green", item_type=t2)
        tag = Tag.insert(db, name="t1", items=[a, b])

        updated = tag.update(
            db,
            items=[
                {
                    "id": a.id,
                    "color": "blue",
                    "item_type": {"id": t1.id, "name": "type_a"},
                },
                {"id": b.id, "color": "magenta", "item_type": None},
                {"color": "green"},
            ],
            on_update_assocs="nilify_all",
        )

        assert len(updated.items) == 3
        assert Item.count(db) == 3
        assert ItemType.count(db) == 2

    def test_conflicting_nilify_does_not_raise(self, db):
        t1 = ItemType.insert(db, name="type_1")
        a = Item.insert(db, color="red", item_type=t1)
        b = Item.insert(db, color="green", item_type=t1)
        tag = Tag.insert(db, name="t1", items=[a, b])

        updated = tag.update(
            db,
            items=[
                {
                    "id": a.id,
                    "color": "blue",
                    "item_type": {"id": t1.id, "name": "type_a"},
                },
                {"id": b.id, "color": "magenta", "item_type": None},
                {"color": "green"},
            ],
            on_update_assocs="nilify_all",
        )

        assert len(updated.items) == 3
        assert ItemType.count(db) == 1

    def test_m2m_clears_join_rows_keeps_items(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        tag = Tag.insert(db, name="t1", items=[a, b])

        updated = tag.update(
            db, items=[{"id": a.id}], on_update_assocs="nilify_all"
        )

        assert len(updated.items) == 1
        assert Item.count(db) == 2
        assert ItemTag.count(db) == 1
