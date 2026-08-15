"""Update commit=False — SQLAlchemy adapter.

``commit=False`` participates in the session without ``session.commit()``
(same idea as insert). Caller commits (or rolls back) later.
"""

from tests.models import Item, ItemList, ItemType


class TestUpdateCommitFalse:
    def test_scalar_pending_until_commit(self, db):
        item = Item.insert(db, color="red")

        updated = item.update(db, color="blue", commit=False)

        assert updated is item
        assert item.color == "blue"
        assert Item.get(db, item.id).color == "blue"

        db.commit()

        assert Item.get(db, item.id).color == "blue"

    def test_belongs_to_pending_until_commit(self, db):
        item_type = ItemType.insert(db, name="type_1")
        other = ItemType.insert(db, name="type_2")
        item = Item.insert(db, color="red", item_type=item_type)

        item.update(db, item_type_id=other.id, commit=False)

        assert item.item_type_id == other.id
        db.commit()
        assert Item.get(db, item.id).item_type_id == other.id

    def test_collection_pending_until_commit(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a])

        lst.update(
            db,
            name="L2",
            items=[a, b],
            on_update_assocs="nilify_all",
            commit=False,
        )

        assert lst.name == "L2"
        assert len(lst.items) == 2
        db.commit()
        assert ItemList.get(db, lst.id).name == "L2"

    def test_nested_create_pending_until_commit(self, db):
        item = Item.insert(db, color="red")

        item.update(db, item_type={"name": "brand_new"}, commit=False)
        db.flush()

        assert item.item_type.name == "brand_new"
        assert ItemType.count(db) == 1

        db.commit()

        assert Item.get(db, item.id).item_type.name == "brand_new"

    def test_delete_all_pending_until_commit(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        lst.update(db, items=[], on_update_assocs="delete_all", commit=False)
        db.flush()

        assert len(lst.items) == 0
        assert Item.count(db) == 0

        db.commit()

        assert Item.count(db) == 0

    def test_commit_true_persists(self, db):
        item = Item.insert(db, color="red")

        item.update(db, color="blue", commit=True)

        assert Item.get(db, item.id).color == "blue"
