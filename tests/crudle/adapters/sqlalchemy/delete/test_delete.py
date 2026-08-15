"""Delete by instance — SQLAlchemy adapter.

Instance ``delete(db)``. Filter dialect lives on ``delete_by``.
"""

import pytest

from tests.models import Item, ItemList, ItemType, Tag


class TestDelete:
    def test_hit(self, db):
        item = Item.insert(db, name="a", color="red")
        item_id = item.id

        result = item.delete(db)

        assert result is item
        assert Item.get(db, item_id) is None

    def test_does_not_cascade_belongs_to(self, db):
        item_type = ItemType.insert(db, name="Electronics")
        item = Item.insert(db, name="Phone", color="red", item_type=item_type)

        item.delete(db)

        assert ItemType.get(db, item_type.id) is not None

    def test_does_not_cascade_has_many_children(self, db):
        a = Item.insert(db, name="a", color="red")
        b = Item.insert(db, name="b", color="blue")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        lst.delete(db)

        assert ItemList.get(db, lst.id) is None
        assert Item.get(db, a.id) is not None
        assert Item.get(db, b.id) is not None

    def test_removes_from_collection(self, db):
        a = Item.insert(db, name="a", color="red")
        b = Item.insert(db, name="b", color="blue")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        a.delete(db)
        db.refresh(lst)

        assert Item.get(db, a.id) is None
        assert len(lst.items) == 1
        assert b in lst.items

    def test_double_delete_is_noop(self, db):
        item = Item.insert(db, color="red")
        item.delete(db)
        assert Item.count(db) == 0

        # Second delete on detached/already-removed instance should not
        # resurrect rows (may warn under SA confirm_deleted_rows).
        item.delete(db)
        assert Item.count(db) == 0

    def test_unpersisted_raises(self, db):
        item = Item(color="red")

        with pytest.raises(Exception):
            item.delete(db)

    def test_commit_false_needs_manual_commit(self, db):
        item = Item.insert(db, color="red")
        item_id = item.id

        item.delete(db, commit=False)
        assert Item.get(db, item_id) is not None

        db.commit()
        assert Item.get(db, item_id) is None

    def test_different_models(self, db):
        item = Item.insert(db, name="a", color="red")
        lst = ItemList.insert(db, name="L1")
        tag = Tag.insert(db, name="t1")

        item.delete(db)
        lst.delete(db)
        tag.delete(db)

        assert Item.count(db) == 0
        assert ItemList.count(db) == 0
        assert Tag.count(db) == 0
