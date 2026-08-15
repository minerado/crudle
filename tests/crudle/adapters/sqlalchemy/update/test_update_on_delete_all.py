"""on_update_assocs=delete_all — SQLAlchemy adapter.

Replace collection: omitted members are deleted.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from tests.models import Item, ItemList, ItemType, Tag


class TestUpdateOnDeleteAll:
    def test_replace_with_existing_and_new(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        updated = lst.update(
            db,
            items=[{"id": a.id, "color": "blue"}, {"color": "yellow"}],
            on_update_assocs="delete_all",
        )

        assert len(updated.items) == 2
        assert Item.count(db) == 2
        # SQLite may reuse deleted PKs; assert by surviving colors.
        assert {i.color for i in Item.list(db)} == {"blue", "yellow"}

    def test_clear_collection_deletes_children(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        updated = lst.update(db, items=[], on_update_assocs="delete_all")

        assert updated.items == []
        assert Item.count(db) == 0

    def test_belongs_to_none_deletes_related(self, db):
        item_type = ItemType.insert(db, name="Electronics")
        item = Item.insert(db, color="red", item_type=item_type)

        updated = item.update(db, item_type=None, on_update_assocs="delete_all")

        assert updated.item_type is None
        assert ItemType.count(db) == 0

    def test_mixed_dict_and_instance(self, db):
        a = Item.insert(db, color="red")
        fresh = Item(color="green")
        lst = ItemList.insert(db, name="L1", items=[a])

        updated = lst.update(
            db,
            items=[{"id": a.id, "color": "blue"}, fresh, {"color": "yellow"}],
            on_update_assocs="delete_all",
        )

        assert len(updated.items) == 3
        assert Item.count(db) == 3

    def test_deep_nested_deletes_cleared_belongs_to(self, db):
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
            on_update_assocs="delete_all",
        )

        assert len(updated.items) == 3
        assert Item.count(db) == 3
        assert ItemType.count(db) == 1

    def test_conflicting_update_and_delete_raises(self, db):
        t1 = ItemType.insert(db, name="type_1")
        a = Item.insert(db, color="red", item_type=t1)
        b = Item.insert(db, color="green", item_type=t1)
        tag = Tag.insert(db, name="t1", items=[a, b])

        with pytest.raises(IntegrityError, match="Conflicting operations on item_type"):
            tag.update(
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
                on_update_assocs="delete_all",
            )
