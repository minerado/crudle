"""Update commit=False — SQLAlchemy adapter.

Returns a working copy with proposed values; rolls back so the DB
(and the original instance after refresh) stay unchanged.

Note: ``commit=False`` copies list relationships as empty collections, so
raise-on-remove detection does not apply on that path.
"""

from tests.models import Item, ItemList, ItemType


class TestUpdateCommitFalse:
    def test_scalar_not_persisted(self, db):
        item = Item.insert(db, color="red")

        updated = item.update(db, color="blue", commit=False)

        assert updated.color == "blue"
        db.refresh(item)
        assert item.color == "red"

    def test_belongs_to_not_persisted(self, db):
        item_type = ItemType.insert(db, name="type_1")
        item = Item.insert(db, color="red", item_type=item_type)

        updated = item.update(
            db,
            item_type={"id": item_type.id, "name": "type_2"},
            commit=False,
        )

        assert updated.item_type.name == "type_2"
        db.refresh(item)
        assert item.item_type.name == "type_1"

    def test_collection_add_not_persisted(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a])

        updated = lst.update(db, name="L2", items=[a, b], commit=False)

        assert updated.name == "L2"
        assert len(updated.items) == 2
        db.refresh(lst)
        assert lst.name == "L1"
        assert len(lst.items) == 1

    def test_nested_create_not_persisted(self, db):
        item = Item.insert(db, color="red")

        updated = item.update(
            db,
            item_type={"name": "brand_new"},
            commit=False,
        )

        assert updated.item_type.name == "brand_new"
        assert ItemType.count(db) == 0

    def test_delete_all_not_persisted(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        updated = lst.update(
            db, items=[], on_update_assocs="delete_all", commit=False
        )

        assert len(updated.items) == 0
        db.refresh(lst)
        assert len(lst.items) == 2
        assert Item.count(db) == 2

    def test_commit_true_persists(self, db):
        item = Item.insert(db, color="red")

        item.update(db, color="blue", commit=True)

        assert Item.get(db, item.id).color == "blue"
