"""on_update_assocs=raise — SQLAlchemy adapter.

Default policy: may add / update members; may not drop existing ones.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from tests.models import Item, ItemList, ItemType, Tag


class TestUpdateOnRaise:
    def test_add_existing_and_new(self, db):
        a = Item.insert(db, color="red")
        lst = ItemList.insert(db, name="L1")

        updated = lst.update(
            db,
            items=[{"id": a.id}, {"color": "blue"}],
            on_update_assocs="raise",
        )

        assert len(updated.items) == 2
        assert Item.count(db) == 2

    def test_update_in_place(self, db):
        a = Item.insert(db, color="red")
        lst = ItemList.insert(db, name="L1", items=[a])

        updated = lst.update(
            db,
            items=[{"id": a.id, "color": "blue"}],
            on_update_assocs="raise",
        )

        assert updated.items[0].id == a.id
        assert updated.items[0].color == "blue"
        assert Item.count(db) == 1

    def test_update_and_add(self, db):
        """raise appends payload onto existing members (duplicate-id quirk)."""
        a = Item.insert(db, color="red")
        lst = ItemList.insert(db, name="L1", items=[a])

        updated = lst.update(
            db,
            items=[{"id": a.id, "color": "blue"}, {"color": "green"}],
            on_update_assocs="raise",
        )

        assert Item.count(db) == 2
        assert any(i.color == "blue" for i in updated.items)
        assert any(i.color == "green" for i in updated.items)

    def test_empty_when_already_empty(self, db):
        lst = ItemList.insert(db, name="L1")

        updated = lst.update(db, items=[], on_update_assocs="raise")

        assert updated.items == []

    def test_remove_raises(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        lst = ItemList.insert(db, name="L1", items=[a, b])

        with pytest.raises(IntegrityError, match="on_update='raise'"):
            lst.update(db, items=[{"id": a.id}], on_update_assocs="raise")

    def test_partial_remove_raises(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        c = Item.insert(db, color="blue")
        lst = ItemList.insert(db, name="L1", items=[a, b, c])

        with pytest.raises(IntegrityError, match="on_update='raise'"):
            lst.update(
                db,
                items=[{"id": a.id}, {"id": b.id}],
                on_update_assocs="raise",
            )

    def test_mixed_dict_and_instance(self, db):
        a = Item.insert(db, color="red")
        fresh = Item(color="green")
        lst = ItemList.insert(db, name="L1")

        updated = lst.update(
            db,
            items=[{"id": a.id, "color": "blue"}, fresh, {"color": "yellow"}],
            on_update_assocs="raise",
        )

        assert len(updated.items) == 3
        assert Item.count(db) == 3

    def test_nested_assoc_update(self, db):
        a = Item.insert(db, color="red")
        tag = Tag.insert(db, name="t1", items=[a])

        updated = tag.update(
            db,
            items=[{"id": a.id, "color": "blue"}],
            on_update_assocs="raise",
        )

        assert updated.items[0].color == "blue"

    def test_nested_assoc_remove_raises(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="green")
        tag = Tag.insert(db, name="t1", items=[a, b])

        with pytest.raises(IntegrityError, match="on_update='raise'"):
            tag.update(db, items=[{"id": a.id}], on_update_assocs="raise")

    def test_belongs_to_set(self, db):
        item = Item.insert(db, color="red")
        item_type = ItemType.insert(db, name="Electronics")

        updated = item.update(
            db,
            item_type={"id": item_type.id},
            on_update_assocs="raise",
        )

        assert updated.item_type_id == item_type.id

    def test_belongs_to_clear_raises(self, db):
        item_type = ItemType.insert(db, name="Electronics")
        item = Item.insert(db, color="red", item_type=item_type)

        with pytest.raises(IntegrityError):
            item.update(db, item_type=None, on_update_assocs="raise")

    def test_duplicate_ids_append(self, db):
        """raise mode appends payload entries — duplicate ids stay duplicated."""
        a = Item.insert(db, color="red")
        lst = ItemList.insert(db, name="L1")

        updated = lst.update(
            db,
            items=[
                {"id": a.id, "color": "blue"},
                {"id": a.id, "color": "green"},
            ],
            on_update_assocs="raise",
        )

        assert len(updated.items) == 2
        assert all(i.id == a.id for i in updated.items)
        assert "green" in [i.color for i in updated.items]
